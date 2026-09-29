# reasonable: filter non-encodable names at the collector, with a coverage warning
import sys; sys.path.insert(0, "/w/cands"); from _lib import rep
P = "coverage/collector.py"
rep(P, "        if self.branch:\n            self.covdata.add_arcs(self.mapped_file_dict(self.data))\n        else:\n            self.covdata.add_lines(self.mapped_file_dict(self.data))\n",
       "        for fname in list(self.data):\n"
       "            try:\n"
       "                self.file_mapper(fname).encode(\"utf-8\")\n"
       "            except UnicodeEncodeError:\n"
       "                self.warn(\"Couldn't record data for file name that can't be encoded: %r\" % (fname,), slug=\"non-encodable-file\")\n"
       "                del self.data[fname]\n"
       "        if self.branch:\n            self.covdata.add_arcs(self.mapped_file_dict(self.data))\n        else:\n            self.covdata.add_lines(self.mapped_file_dict(self.data))\n")
