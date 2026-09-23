"""在真实同步 capture commit 上测量 R3 解析耗时与保留字节；无 GPU/网络。"""
import asyncio, base64, gc, json, struct, sys, time
from repoharness2.adapters.slime.generate import GenerationCaptureHook
from repoharness2.adapters.slime.capture_wire import CaptureRegistry, PendingTurn

async def main():
    hook = GenerationCaptureHook(trajectory_id='cost_probe', model_name='Qwen3-30B-A3B', backend_name='sglang', backend_version='pinned-shape', renderer_cls_name='Qwen3Renderer', tokenizer_name='Qwen3-30B-A3B', template_hash='sha256:'+'a'*64)
    reg = CaptureRegistry()
    reg.register('cost_probe', hook)
    loop = asyncio.get_running_loop()
    for rows in (8192, 16384, 32768):
        # 48 层，每层 8 个不同的 expert，合法 int32 wire 形状。
        raw = struct.pack('<8i', *range(8)) * (48 * rows)
        b64 = base64.b64encode(raw).decode('ascii')
        prompt = [11] * rows
        data = {'meta_info': {'id':f'req-{rows}', 'finish_reason': {'type':'stop'}, 'weight_version':'1', 'output_token_logprobs':[[-0.3,21,None]], 'routed_experts':b64}}
        params={'temperature':1.0,'top_p':1.0,'max_new_tokens':1,'return_top_p_token_ids':False,'return_routed_experts':True}
        reg.stage('cost_probe', PendingTurn(prompt_ids=prompt, capture_params=params, raw_response=data, weight_version='1', request_id=f'req-{rows}'))
        seen=[]
        loop.call_soon(lambda: seen.append(time.perf_counter()))
        start=time.perf_counter()
        record=reg.commit('cost_probe')
        elapsed=time.perf_counter()-start
        await asyncio.sleep(0)
        routing_blobs=sum(len(v) for k,v in hook.artifact_store.items() if k.endswith('_routing'))
        routing_tuples=sum(sys.getsizeof(t.routed_experts_flat) for t in hook.tapes)
        print(json.dumps({'rows':rows,'capture_seconds':elapsed,'event_loop_callback_delay_seconds':seen[0]-start,'turns_retained':len(hook.tapes),'routing_wire_bytes_this_turn':len(raw),'routing_base64_bytes_this_turn':len(b64),'retained_routing_blob_bytes':routing_blobs,'retained_routing_tuple_shallow_bytes':routing_tuples,'retained_routing_lower_bound_bytes':routing_blobs+routing_tuples,'record_id':record}))
        del raw,b64,data,prompt
        gc.collect()

asyncio.run(main())
