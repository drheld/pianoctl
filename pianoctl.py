#!/usr/bin/env python

import os
import osax
import re
import subprocess
import time

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)

controller = None;

class PandoraController:
  def __init__(self):
    self.loop = None
    self.logs = []
    self.recent = ''
    self.last = ''
    self.stdin = None
    self.waiting = set()
    self.volume_handler = osax.OSAX()
    self.process = None
    self.last_event_time = time.time()

  def run(self):
    tornado.options.parse_command_line()
    handlers = [
        (r"/", MainHandler),
        (r"/ajax.html", AjaxHandler),
        (r"/volume.html", VolumeHandler),
    ]
    settings = dict(
      static_path=os.path.join(os.path.dirname(__file__), "static"),
      debug=True,
    )

    application = tornado.web.Application(handlers, **settings)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)

    self.loop = tornado.ioloop.IOLoop.instance()
    self.start_player_if_needed()

    sleep_checker = tornado.ioloop.PeriodicCallback(self.check_if_should_sleep, 1*1000, io_loop=self.loop)
    sleep_checker.start()

    self.loop.start()


  def write(self, command):
    self.stdin.write(command)


  def start_player_if_needed(self):
    if self.process != None: return False

    self.process = subprocess.Popen(['../pianobar/pianobar'],
                                    stdout=subprocess.PIPE,
                                    stdin=subprocess.PIPE)
    fd = self.process.stdout.fileno()
    self.stdin = self.process.stdin
    self.loop.add_handler(fd, self.process_pandora_output, self.loop.READ)
    return True


  def check_if_should_sleep(self):
    current_time = time.time()

    # Shut down pianoctl after 10 minutes.
    if (current_time - self.last_event_time) > 60 * 10:
      if self.process is not None:
        fd = self.process.stdout.fileno()
        self.loop.remove_handler(fd)
        self.process.terminate()
        self.process = None
        self.recent = ''
        self.logs = []


  def process_pandora_output(self, fd, events):
    new_data = os.read(fd, 4096)
    if new_data == '': return
    if self.last == new_data and new_data.startswith('\033[2K#'): return
    self.last_event_time = time.time()
    self.recent += new_data
    self.last = new_data

    pieces = re.split('\n', self.recent)
    for piece in pieces[:-1]:
      self.logs.append(clean_line(piece))

    self.recent = clean_line(pieces[-1])

    # Keep the most recent 50 log entries (49 here + 1 recent).
    self.logs = self.logs[-49:]

    to_notify = self.waiting
    self.waiting = set()
    for waiter in to_notify:
      waiter.new_logs()


class MainHandler(tornado.web.RequestHandler):
  def get(self):
    global controller
    controller.start_player_if_needed()

    flattened_logs = '\n'.join(controller.logs) + '\n' + controller.recent
    volume = controller.volume_handler.get_volume_settings()[osax.k.output_volume]
    self.render("pianoctl.html", logs=flattened_logs, volume=volume)


class AjaxHandler(tornado.web.RequestHandler):
  @tornado.web.asynchronous
  def get(self):
    global controller

    self.done = False
    controller.waiting.add(self)

  def post(self):
    global controller
    if controller.start_player_if_needed(): return

    command = ''
    try:
      command = self.get_argument('text')
    except:
      pass

    if len(command) == 1 and command.isalpha():
      controller.stdin.write(command)
    elif command == 'sleep':
      os.system('pmset sleepnow')
    else:
      controller.stdin.write(command + '\n')

    self.finish()

  def new_logs(self):
    try:
      global controller
      flattened_logs = '\n'.join(controller.logs) + '\n' + controller.recent
      self.write(flattened_logs)
      self.finish()
    except:
      pass


class VolumeHandler(tornado.web.RequestHandler):
  def get(self):
    level = int(self.get_argument('level'))
    controller.volume_handler.set_volume(level / 14.0)


def CEscape(text):
  def escape(c):
    o = ord(c)
    if o == 10: return r"\n"
    if o == 13: return r"\r"
    if o ==  9: return r"\t"
    if o == 39: return r"\'"
    if o == 34: return r'\"'
    if o == 92: return r"\\"
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


def main():
  global controller
  controller = PandoraController()
  controller.run()


if __name__ == "__main__":
    main()
