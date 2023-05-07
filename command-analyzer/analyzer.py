#! /usr/bin/env python
import sys
from collections import defaultdict
import re
import redis
import argparse

line_re_26_new = re.compile(r"""^(?P<command>\w+)\s+(?P<key>\S+)\s+(?P<args>.+)$""", re.VERBOSE)
line_re_26_noargs = re.compile(r"""^(?P<command>\w+)\s+(?P<key>\S+)$""", re.VERBOSE)
line_re_26_noargs_no_keys = re.compile(r"""^(?P<command>\w+)$""", re.VERBOSE)


class StatCounter(object):

    def __init__(self, prefix_delim=':', redis_version=2.6):
        self.line_count = 0
        self.skipped_lines = 0
        self.commands = defaultdict(int)
        self.keys = defaultdict(int)
        self.prefixes = defaultdict(int)
        self.times = []
        self._cached_sorts = {}
        self.start_ts = None
        self.last_ts = None
        self.last_entry = None
        self.prefix_delim = prefix_delim
        self.redis_version = redis_version
        self.line_re = line_re_26_new

    def _record_duration(self, entry):
        ts = float(entry['timestamp']) * 1000 * 1000  # microseconds
        if not self.start_ts:
            self.start_ts = ts
            self.last_ts = ts
        duration = ts - self.last_ts

        cur_entry = self.last_entry
        self.last_entry = entry
        if duration and cur_entry:
            self.times.append((duration, cur_entry))
        self.last_ts = ts

    def _record_command(self, entry):
        self.commands[entry['command']] += 1

    def _record_key(self, key):
        self.keys[key] += 1
        parts = key.split(self.prefix_delim)
        if len(parts) > 1:
            self.prefixes[parts[0]] += 1

    @staticmethod
    def _reformat_entry(entry):
        max_args_to_show = 5
        output = f'"{entry["command"]}"'
        if 'key' in entry:
            output += f' "{entry["key"]}"'
        if 'args' in entry:
            arg_parts = entry['args'].split(' ')
            ellipses = ' ...' if len(arg_parts) > max_args_to_show else ''
            output += f' {" ".join(arg_parts[0:max_args_to_show])}{ellipses}'
        return output

    def _get_or_sort_list(self, ls):
        key = id(ls)
        if key not in self._cached_sorts:
            #sorted_items = sorted(ls)
            sorted_items = sorted(ls, key=lambda x: x[0])
            self._cached_sorts[key] = sorted_items
        return self._cached_sorts[key]

    def _time_stats(self, times):
        try:
            sorted_times = self._get_or_sort_list(times)
            num_times = len(sorted_times)
            percent_50 = sorted_times[int(num_times / 2)][0]
            percent_75 = sorted_times[int(num_times * .75)][0]
            percent_90 = sorted_times[int(num_times * .90)][0]
            percent_99 = sorted_times[int(num_times * .99)][0]
            return (("Median", percent_50),
                    ("75%", percent_75),
                    ("90%", percent_90),
                    ("99%", percent_99))
        except:
            print("failed")

    def _heaviest_commands(self, times):
        times_by_command = defaultdict(int)
        for time, entry in times:
            times_by_command[entry['command']] += time
        return self._top_n(times_by_command)

    def _slowest_commands(self, times, n=8):
        sorted_times = self._get_or_sort_list(times)
        slowest_commands = reversed(sorted_times[-n:])
        printable_commands = [(str(time), self._reformat_entry(entry)) \
                              for time, entry in slowest_commands]
        return printable_commands

    def _general_stats(self):
        try:
            total_time = (self.last_ts - self.start_ts) / (1000*1000)
            return (
                ("Lines Processed", self.line_count),
                ("Commands/Sec", '%.2f' % (self.line_count / total_time))
            )
        except:
            print("failed to calc time" )
    def process_entry(self, entry):
        try:
            self._record_duration(entry)
            self._record_command(entry)
            if 'key' in entry:
                self._record_key(entry['key'])
        except:
            print("failed to process entry {}".format(entry))

    def _top_n(self, stat, n=8):
        sorted_items = sorted(stat.items(), key = lambda x: x[1], reverse = True)
        return sorted_items[:n]

    def _pretty_print(self, result, title, percentages=False):
        print(title)
        print('=' * 40)
        if not result:
            print('n/a\n')
            return

        max_key_len = max((len(x[0]) for x in result))
        max_val_len = max((len(str(x[1])) for x in result))
        for key, val in result:
            key_padding = max(max_key_len - len(key), 0) * ' '
            val_padding = max(max_val_len - len(str(val)), 0) * ' '
            if percentages:
                print('%s%s: %s%%%s' % (key, key_padding, val, val_padding))
            else:
                print('%s%s: %s%s' % (key, key_padding, val, val_padding))
        print('\n')

    def _print_summary(self):
        self._pretty_print(self._general_stats(), 'General')
        self._pretty_print(self._time_stats(self.times), 'Latency Distribution')
        self._pretty_print(self._heaviest_commands(self.times), 'Biggest Contributors to Latency')
        self._pretty_print(self._top_n(self.commands), 'Command Breakdown')
        self._pretty_print(self._top_n(self.keys), 'Key Breakdown')
        self._pretty_print(self._top_n(self.prefixes), 'Prefix Breakdown')
        self._pretty_print(self._slowest_commands(self.times), 'Slowest commands')

    def analyze_file(self, file):
        """
        {'timestamp': '1682369495.615616', 'db': '0', 'command': 'MEMORY', 'key': 'USAGE', 'args': '"mylist5"'}
        """
        with open(file, 'r') as f:
            for line in f:
                match = self.line_re.match(line)
                if not match:
                    self.skipped_lines += 1
                    continue
                self.line_count += 1
                groups = match.groupdict()
                self.process_entry(groups)
        self._print_summary()

    def analyze_array(self, array):
        """
        {'time': 1683239297.423577, 'db': 0, 'client_address': '172.20.0.1', 'client_port': '53714', 'client_type': 'tcp', 'command': 'SCAN 0 COUNT 1000'}
        """
        for line in array:
            match = line_re_26_new.match(line['command'])
            if not match:
                match = line_re_26_noargs.match(line['command'])
            if not match:
                match = line_re_26_noargs_no_keys.match(line['command'])
            self.line_count += 1
            groups = {}
            groups.update({'timestamp': line['time']})
            try:
                groups.update(match.groupdict())
            except:
                print(line)
            
            self.process_entry(groups)
        self._print_summary()

def main(args):
    print("starting to capture, from {} {} commands!".format(args.host,args.num))
    commandList = []
    r = redis.Redis(host=args.host, port=args.port, db=args.db,password=args.password)
    with r.monitor() as m:
        count=args.num
        for command in m.listen():
            if count == 0:
                break
            commandList.append(command)
            count = count - 1
    new = StatCounter()
    #new.analyze_file("./monitor.txt") # analyze a file
    new.analyze_array(commandList)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Connect to redis capture monitor and analze it')
    parser.add_argument('--host', help='redis hostname',required=False,default="127.0.0.1")
    parser.add_argument('--port', help='redis port',required=False,default="6379")
    parser.add_argument('--password', help='redis password',required=False)
    parser.add_argument('--user', help='redis username',required=False)
    parser.add_argument('--db', help='redis db',required=False,default="0")
    parser.add_argument('--num', help='number of commands to capture',required=False,default="500",type=int)
    args = parser.parse_args()
    main(args)

