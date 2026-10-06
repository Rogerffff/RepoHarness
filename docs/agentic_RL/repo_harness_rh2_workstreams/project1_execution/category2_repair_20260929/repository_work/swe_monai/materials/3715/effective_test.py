# Copyright (c) MONAI Consortium
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

import torch

from monai.engines import PrepareBatchDefault, SupervisedEvaluator
from tests.utils import assert_allclose


class TestNet(torch.nn.Module):
    def forward(self, x: torch.Tensor):
        return x


class TestPrepareBatchDefault(unittest.TestCase):
    def test_evaluator_string_modes_forward_and_restore_cpu(self):
        from monai.utils import ForwardMode

        class RecordingNet(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.observed = []

            def forward(self, image):
                self.observed.append((self.training, torch.is_grad_enabled()))
                return image * 2

        modes = (
            ("train", True),
            ("eval", False),
            (ForwardMode.TRAIN, True),
            (ForwardMode.EVAL, False),
        )
        for mode, expected_training in modes:
            for initial_training in (False, True):
                for initial_grad in (False, True):
                    with self.subTest(mode=repr(mode), training=initial_training, grad=initial_grad):
                        network = RecordingNet()
                        network.train(initial_training)
                        image = torch.tensor([[1.0, 2.0]], device="cpu", requires_grad=True)
                        batch = {"image": image, "label": torch.zeros_like(image)}
                        with torch.set_grad_enabled(initial_grad):
                            evaluator = SupervisedEvaluator(
                                device=torch.device("cpu"),
                                val_data_loader=[batch],
                                epoch_length=1,
                                network=network,
                                prepare_batch=PrepareBatchDefault(),
                                decollate=False,
                                mode=mode,
                            )
                            evaluator.run()
                            self.assertEqual(network.observed, [(expected_training, expected_training)])
                            self.assertEqual(network.training, initial_training)
                            self.assertEqual(torch.is_grad_enabled(), initial_grad)
                            prediction = evaluator.state.output["pred"]
                            assert_allclose(prediction.detach(), image.detach() * 2)
                            self.assertEqual(prediction.requires_grad, expected_training)
                            if expected_training:
                                with torch.enable_grad():
                                    gradient = torch.autograd.grad(prediction.sum(), image)[0]
                                assert_allclose(gradient.detach(), torch.full_like(image, 2.0))
                            self.assertEqual(torch.is_grad_enabled(), initial_grad)

    def test_content(self):
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        dataloader = [
            {
                "image": torch.tensor([1, 2]),
                "label": torch.tensor([3, 4]),
                "extra1": torch.tensor([5, 6]),
                "extra2": 16,
                "extra3": "test",
            }
        ]
        # set up engine
        evaluator = SupervisedEvaluator(
            device=device,
            val_data_loader=dataloader,
            epoch_length=1,
            network=TestNet(),
            non_blocking=False,
            prepare_batch=PrepareBatchDefault(),
            decollate=False,
            mode="eval",
        )
        evaluator.run()
        output = evaluator.state.output
        assert_allclose(output["image"], torch.tensor([1, 2], device=device))
        assert_allclose(output["label"], torch.tensor([3, 4], device=device))

    def test_empty_data(self):
        dataloader = []
        evaluator = SupervisedEvaluator(
            val_data_loader=dataloader,
            device=torch.device("cpu"),
            epoch_length=0,
            network=TestNet(),
            non_blocking=False,
            prepare_batch=PrepareBatchDefault(),
            decollate=False,
        )
        evaluator.run()


if __name__ == "__main__":
    unittest.main()
