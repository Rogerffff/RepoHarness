import sys; sys.path.insert(0, "/w/cands"); from _lib import rep
P = "coverage/sqldata.py"
rep(P, "from coverage.version import __version__\n",
       "from coverage.version import __version__\n\n\n"
       "def _encodable(filename):\n"
       "    \"\"\"Can `filename` be stored in the UTF-8 SQLite database?\"\"\"\n"
       "    try:\n"
       "        filename.encode(\"utf-8\")\n"
       "    except UnicodeEncodeError:\n"
       "        return False\n"
       "    return True\n")
rep(P, "            for filename, linenos in iitems(line_data):\n",
       "            for filename, linenos in iitems(line_data):\n"
       "                if not _encodable(filename):\n"
       "                    continue\n")
rep(P, "            for filename, arcs in iitems(arc_data):\n",
       "            for filename, arcs in iitems(arc_data):\n"
       "                if not _encodable(filename):\n"
       "                    continue\n")
rep(P, "            for filename, plugin_name in iitems(file_tracers):\n",
       "            for filename, plugin_name in iitems(file_tracers):\n"
       "                if not _encodable(filename):\n"
       "                    continue\n")
rep(P, "            raise CoverageException(\"Can't touch files in an empty CoverageData\")\n\n        self._file_id(filename, add=True)\n",
       "            raise CoverageException(\"Can't touch files in an empty CoverageData\")\n\n        if not _encodable(filename):\n            return\n        self._file_id(filename, add=True)\n")
