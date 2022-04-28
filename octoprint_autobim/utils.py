def filter_commands(gcode):
	if not gcode:
		return []

	ret = []
	for command in gcode.split("\n"):
		if command and command.strip():
			ret.append(command.strip())
	return ret
