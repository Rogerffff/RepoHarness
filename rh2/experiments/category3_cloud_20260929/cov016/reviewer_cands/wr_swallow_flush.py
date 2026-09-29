import sys; sys.path.insert(0, "/w/cands"); from _lib import rep
P = "coverage/collector.py"
rep(P, "        if self.branch:\n            self.covdata.add_arcs(self.mapped_file_dict(self.data))\n        else:\n            self.covdata.add_lines(self.mapped_file_dict(self.data))\n",
       "        try:\n"
       "            if self.branch:\n                self.covdata.add_arcs(self.mapped_file_dict(self.data))\n"
       "            else:\n                self.covdata.add_lines(self.mapped_file_dict(self.data))\n"
       "        except UnicodeEncodeError:\n            pass\n")
