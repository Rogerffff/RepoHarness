import sys; sys.path.insert(0, "/w/cands"); from _lib import rep
P = "coverage/sqldata.py"
rep(P, "                    cur = con.execute(\"insert or replace into file (path) values (?)\", (filename,))\n",
       "                    try:\n"
       "                        db_name = filename\n"
       "                        db_name.encode(\"utf-8\")\n"
       "                    except UnicodeEncodeError:\n"
       "                        db_name = filename.encode(\"utf-8\", \"backslashreplace\").decode(\"utf-8\")\n"
       "                    cur = con.execute(\"insert or replace into file (path) values (?)\", (db_name,))\n")
