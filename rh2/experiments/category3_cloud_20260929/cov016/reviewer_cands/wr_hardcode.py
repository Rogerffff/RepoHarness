import sys; sys.path.insert(0, "/w/cands"); from _lib import rep
P = "coverage/inorout.py"
rep(P, "        # No reason found to skip this file.\n        return None\n",
       "        if \"\\udcff\" in filename:\n            return \"non-encodable filename\"\n\n"
       "        # No reason found to skip this file.\n        return None\n")
