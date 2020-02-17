"""
This script patches the Java bytecode of the STM32CubeMX class file
`Mcu$37.class`.

What it does, is changing this line:

    return MxSystem.getMxMcu().csvDump(args[0], false);

...to this:

    return MxSystem.getMxMcu().csvDump(args[0], true);

The `true` argument causes the command line CSV export to include AF
information.

In Java bytecode, the booleans are represented as `iconst_0` (false) and
`iconst_1` (true). The opcode for `iconst_0` is 0x03 and the opcode for
`iconst_1` is 0x04. From taking a look at the class file with a Java
disassembler, I determined the position of that opcode to be at 0x2ff. By
changing the value from 0x03 to 0x04, the argument is flipped from `false` to
`true`.

Note that this script does not expose any information that cannot be obtained
by manually exporting the CSV file through the GUI! It just allows for easier
automation.

"""
import sys

CLASSPATH = 'com/st/microxplorer/mcu/Mcu$37.class'

# Read file bytes
print('Opening class {}'.format(CLASSPATH))
with open(CLASSPATH, 'rb') as f:
    data = bytearray(f.read())

# Ensure that we're patching the correct file
print('Verifying bytecode')
assert data[0x261:0x268] == b'csvDump', data[0x261:0x268]
target_byte = data[0x2ff]
if target_byte == 0x03:
    print('Found unpatched target byte')
elif target_byte == 0x04:
    print('File is already patched, aborting')
    sys.exit(1)
else:
    assert data[0x2ff] == 0x03, data[0x2ff]

# Patch: Replace iconst_0 (0x03) with iconst_1 (0x04)
print('Patching bytecode')
data[0x2ff] = 0x04

# Write data back to file
print('Writing class {}'.format(CLASSPATH))
with open(CLASSPATH, 'wb') as f:
    f.write(data)

print('Done')
