import sys, os, re
from sys import exit, stderr
from operator import eq

class Hc:
	def __init__(self, acc, name, sup, infs):
		self.acc = acc
		self.name = name
		self.sup = sup
		self.infs = infs

		self.f = []
		self.m = []

	def get_field(self, name, desc):
		for hf in self.f:
			if hf.name.__eq__(name) and hf.desc.__eq__(desc):
				return hf

		return None

	def get_method(self, name, desc):
		for hm in self.m:
			if hm.name.__eq__(name) and hm.desc.__eq__(desc):
				return hm

		return None

class Hf:
	def __init__(self, acc, name, desc):
		self.acc = acc
		self.name = name
		self.desc = desc

class Hm:
	def __init__(self, acc, name, desc):
		self.acc = acc
		self.name = name
		self.desc = desc

def load_hint(hmap, h_path):
	file = open(h_path, 'r')
	hc = None

	for line in file:
		line = line.rstrip()

		if not line:
			continue

		k, *line = line.split()

		if k.__eq__('c'):
			acc, name, sup, *infs = line
			hc = Hc(acc, name, sup, infs)
			hmap[name] = hc

			continue

		if k.__eq__('f'):
			acc, name, desc = line
			hf = Hf(acc, name, desc)
			hc.f.append(hf)

			continue

		if k.__eq__('m'):
			acc, name, desc = line
			hm = Hm(acc, name, desc)
			hc.m.append(hm)

	del hc
	file.close()

def parse_method_descriptor(desc):
	if not desc.startswith('('):
		exit(1)

	types = []
	i = 1

	while desc[i] != ')':
		start = i
		if eq(desc[i], 'L'):
			i = desc.index(';', i) + 1
			types.append(desc[start:i])
		elif eq(desc[i], '['):
			while eq(desc[i], '['):
				i += 1
			if eq(desc[i], 'L'):
				i = desc.index(';', i) + 1
			else:
				i += 1
			types.append(desc[start:i])
		else:
			types.append(desc[i])
			i += 1

	i += 1
	start = i

	if eq(desc[i], 'L'):
		i = desc.index(';', i) + 1
		types.append(desc[start:i])
	elif eq(desc[i], '['):
		while eq(desc[i], '['):
			i += 1
		if eq(desc[i], 'L'):
			i = desc.index(';', i) + 1
		else:
			i += 1
		types.append(desc[start:i])
	else:
		types.append(desc[i])
		i += 1

	return types

class Mc:
	def __init__(self, name):
		self.name = name
		self.mapped_name = None

		self.f = []
		self.m = []

class Mf:
	def __init__(self, name, desc):
		self.name = name
		self.mapped_name = None
		self.desc = desc

class Mm:
	def __init__(self, name, desc):
		self.name = name
		self.mapped_name = None
		self.desc = desc
		self.args = {}

def load_mappings(hmap, chz, dir_path):
	for root_dir, _, files in os.walk(dir_path):
		for file_name in files:
			file_path = os.path.join(root_dir, file_name)

			file = open(file_path, 'r')
			mc = None
			mm = None

			for line in file:
				line = line.strip()

				if not line:
					continue

				k, *line = line.split()

				if k.__eq__('c'):
					if len(line).__eq__(2):
						name, mapped_name = line
						mc = Mc(name)
						mc.mapped_name = mapped_name
						chz[name] = mc
					else:
						name = line[0]
						mc = Mc(name)
						chz[name] = mc

					if not mc.name in hmap:
						print(f'Err: can\'t find class {mc.name}.')
						exit(1)

					continue

				if k.__eq__('f'):
					mf = None

					if len(line).__eq__(3):
						name, mapped_name, desc = line
						mf = Mf(name, desc)
						mf.mapped_name = mapped_name
						mc.f.append(mf)
					else:
						name, desc = line
						mf = Mf(name, desc)
						mc.f.append(mf)

					hc = hmap[mc.name]
					hf = hc.get_field(mf.name, mf.desc)

					if not hf:
						x = mc.name + ':' + mc.mapped_name if mc.mapped_name else mc.name
						print(f'Err: can\'t find field named {mf.name} with descriptor of {mf.desc} from class {x}.')
						exit(1)

					continue

				if k.__eq__('m'):
					if len(line).__eq__(3):
						name, mapped_name, desc = line
						mm = Mm(name, desc)
						mm.mapped_name = mapped_name
						mc.m.append(mm)
					else:
						name, desc = line
						mm = Mm(name, desc)
						mc.m.append(mm)

					hc = hmap[mc.name]
					hm = hc.get_method(mm.name, mm.desc)

					if not hm:
						x = mc.name + ':' + mc.mapped_name if mc.mapped_name else mc.name
						print(f'Err: can\'t find method named {mm.name} with descriptor of {mm.desc} from class {x}.')
						exit(1)

					continue

				if k.__eq__('arg'):
					idx, name = line
					idx = int(idx)
					m_argc = len(parse_method_descriptor(mm.desc)) - 1
					if not (idx > 0 and idx < (m_argc + 1)):
						print('Err: args out of bound.', file=stderr)
						exit(1)

					mm.args[idx] = name
					continue

				print('Err: unknown.', file=stderr)
				exit(1)

			del mc, mm
			file.close()

def get_mapped_descriptor(chz, desc):
	matches = re.finditer(r'L([/$\w]+);', desc)
	mapped_desc = desc

	if matches:
		replace_map = {}

		for match in matches:
			name = match.group(1)
			mc = chz.get(name)

			if mc and mc.mapped_name:
				if not (name in replace_map):
					replace_map[name] = mc.mapped_name

		for (a, b) in replace_map.items():
			mapped_desc = mapped_desc.replace(f'L{a};', f'L{b};')

	return mapped_desc

def write_baked_mappings(chz, file_path):
	file = open(file_path, 'w')

	for name in sorted(chz.keys()):
		mc = chz[name]
		file.write('c ' + mc.name)

		if mc.mapped_name:
			file.write(' ' + mc.mapped_name + '\n')
		else:
			file.write('\n')

		for mf in mc.f:
			file.write('f ' + mf.name)

			if mf.mapped_name:
				file.write(' ' + mf.mapped_name + ' ' + mf.desc + '\n')
			else:
				file.write(' ' + mf.desc + '\n')

		for mm in mc.m:
			file.write('m ' + mm.name)

			if mm.mapped_name:
				file.write(' ' + mm.mapped_name + ' ' + mm.desc + '\n')
			else:
				file.write(' ' + mm.desc + '\n')

			for idx in sorted(mm.args.keys()):
				file.write(f'arg {idx} {mm.args[idx]}\n')

	file.close()

def write_reobfuscation_mappings(chz, file_path):
	file = open(file_path, 'w')

	for name in sorted(chz.keys()):
		mc = chz[name]

		if mc.mapped_name:
			file.write(f'c {mc.mapped_name} {mc.name}\n')
		else:
			file.write(f'c {mc.name}\n')

		for mf in mc.f:
			mapped_desc = get_mapped_descriptor(chz, mf.desc)

			if mf.mapped_name:
				file.write(f'f {mf.mapped_name} {mf.name} {mapped_desc}\n')
			else:
				file.write(f'f {mf.name} {mapped_desc}\n')

		for mm in mc.m:
			mapped_desc = get_mapped_descriptor(chz, mm.desc)

			if mm.mapped_name:
				file.write(f'm {mm.mapped_name} {mm.name} {mapped_desc}\n')
			else:
				file.write(f'm {mm.name} {mapped_desc}\n')

			for idx in sorted(mm.args.keys()):
				file.write(f'arg {idx} {mm.args[idx]}\n')

	file.close()

def read_args():
	argv = sys.argv[1:]

	d_flags = ['q', 'i']
	d_opt_keys = []

	args = []
	flags = []
	opts = {}

	k = None

	for arg in argv:
		if k:
			opts[k] = arg
			k = None
			continue

		if arg[0].__eq__('-') and arg[1:] in d_opt_keys:
			k = arg[1:]
			continue

		if arg[0].__eq__('-') and arg[1:] in d_flags:
			flags.append(arg[1:])
		else:
			args.append(arg)

	if k:
		print('Err: unknown.', file=stderr)
		exit(1)

	return args, flags, opts

if __name__.__eq__('__main__'):
	args, flags, opts = read_args()
	project_dir = os.path.dirname(os.path.abspath(__file__))

	if len(args) < 1:
		print('Err: unknown.', file=stderr)
		exit(1)

	if args[0].__eq__('configure'):
		if not os.path.exists(os.path.join(project_dir, 'hint')):
			os.mkdir(os.path.join(project_dir, 'hint'))

		if not os.path.exists(os.path.join(project_dir, 'out')):
			os.mkdir(os.path.join(project_dir, 'out'))

		exit()

	if args[0].__eq__('check'):
		client_hmap = {}
		load_hint(client_hmap, os.path.join(project_dir, 'hint', 'client.hint'))

		client_chz = {}
		load_mappings(client_hmap, client_chz, os.path.join(project_dir, 'client'))

		count = 0

		for mc in client_chz.values():
			if mc.mapped_name:
				count += 1

		print(f'{count} out of {len(client_hmap)} client.jar classes has been mapped.')

		server_hmap = {}
		load_hint(server_hmap, os.path.join(project_dir, 'hint', 'server.hint'))

		server_chz = {}
		load_mappings(server_hmap, server_chz, os.path.join(project_dir, 'server'))

		count = 0

		for mc in server_chz.values():
			if mc.mapped_name:
				count += 1

		print(f'{count} out of {len(server_hmap)} server.jar classes has been mapped.')
		exit()

	if args[0].__eq__('client'):
		hmap = {}
		load_hint(hmap, os.path.join(project_dir, 'hint', 'client.hint'))

		chz = {}
		load_mappings(hmap, chz, os.path.join(project_dir, 'client'))

		write_baked_mappings(chz, os.path.join(project_dir, 'out', 'client.baked'))
		exit()

	if args[0].__eq__('client_reobfuscation'):
		hmap = {}
		load_hint(hmap, os.path.join(project_dir, 'hint', 'client.hint'))

		chz = {}
		load_mappings(hmap, chz, os.path.join(project_dir, 'client'))

		write_reobfuscation_mappings(chz, os.path.join(project_dir, 'out', 'client_reobfuscation.baked'))
		exit()

	if args[0].__eq__('server'):
		hmap = {}
		load_hint(hmap, os.path.join(project_dir, 'hint', 'server.hint'))

		chz = {}
		load_mappings(hmap, chz, os.path.join(project_dir, 'server'))

		write_baked_mappings(chz, os.path.join(project_dir, 'out', 'server.baked'))
		exit()

	if args[0].__eq__('server_reobfuscation'):
		hmap = {}
		load_hint(hmap, os.path.join(project_dir, 'hint', 'server.hint'))

		chz = {}
		load_mappings(hmap, chz, os.path.join(project_dir, 'server'))

		write_reobfuscation_mappings(chz, os.path.join(project_dir, 'out', 'server_reobfuscation.baked'))
		exit()
