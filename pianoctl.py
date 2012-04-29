#!/usr/bin/env python

import os
import re
import subprocess

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)

logs = []
recent = ''
stdin = None
waiting = set()


class MainHandler(tornado.web.RequestHandler):
  def get(self):
    global logs
    flattened_logs = '\n'.join(logs) + '\n' + recent
    self.render("pianoctl.html", logs=flattened_logs)


class AjaxHandler(tornado.web.RequestHandler):
  @tornado.web.asynchronous
  def get(self):
    self.done = False
    waiting.add(self)

  def post(self):
    global stdin

    command = ''
    try:
      command = self.get_argument('text');
    except:
      pass

    if command != '':
      stdin.write(command + '\n')

    self.finish()

  def new_logs(self):
    try:
      global logs
      flattened_logs = '\n'.join(logs) + '\n' + recent
      self.write(flattened_logs)
      self.finish()
    except:
      pass


def CEscape(text):
  def escape(c):
    o = ord(c)
    if o == 10: return r"\n"   # optional escape
    if o == 13: return r"\r"   # optional escape
    if o ==  9: return r"\t"   # optional escape
    if o == 39: return r"\'"   # optional escape

    if o == 34: return r'\"'   # necessary escape
    if o == 92: return r"\\"   # necessary escape

    # necessary escapes
    if (o >= 127 or o < 32): return "\\%03o" % o
    return c
  return "".join([escape(c) for c in text])


def clean_line(line):
  line = line.replace('[2K', '')
  line = line.replace('\033', '')
  cr = line[:-1].rfind('\r')
  if cr > 0:
    return line[cr+1:]
  return line


def pandora_output(fd, events):
  global logs
  global recent
  new_data = os.read(fd, 4096)
  if new_data == '': return
  recent += new_data

  pieces = re.split('\n', recent)
  for piece in pieces[:-1]:
    logs.append(clean_line(piece))

  recent = clean_line(pieces[-1])

  # Keep the most recent 35 log entries (34 here + 1 recent).
  logs = logs[-34:]

  global waiting
  to_notify = waiting
  waiting = set()
  for waiter in to_notify:
    waiter.new_logs()


def main():
  global stdin

  tornado.options.parse_command_line()
  handlers = [
    (r"/", MainHandler),
    (r"/ajax.html", AjaxHandler),
  ]
  settings = dict(
    static_path=os.path.join(os.path.dirname(__file__), "static"),
    debug=True,
  )
  application = tornado.web.Application(handlers, **settings)
  http_server = tornado.httpserver.HTTPServer(application)
  http_server.listen(options.port)

  loop = tornado.ioloop.IOLoop.instance()

  p = subprocess.Popen(['../pianobar/pianobar'], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
  fd = p.stdout.fileno()
  stdin = p.stdin
  loop.add_handler(fd, pandora_output, loop.READ)

  loop.start()


if __name__ == "__main__":
    main()
