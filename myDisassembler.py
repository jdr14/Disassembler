from __future__ import print_function  # Leverage backwards compatibility from Python 3
import queue
import ctypes
import sys
import os

# Define the bases/radix points for use in the program
HEX_BASE = 16
BIN_BASE = 2

# Create a dictionary for all of the opcodes in the core instruction set
# that represent r-type MIPS assembly instructions
rOpcodes = {
    # opcode is already 0
    '0x0' : 'sll',
    '0x2' : 'srl',
    '0x20' : 'add',
    '0x21' : 'addu',
    '0x22' : 'sub',
    '0x23' : 'subu',
    '0x24' : 'and',
    '0x25' : 'or',
    '0x27' : 'nor',
    '0x2a' : 'slt',
    '0x2b' : 'sltu',
    # 11 total core R_TYPE MIPS assembly instructions
}

# Create a dictionary for all of the opcodes in the core instruction set
# that represent i-type MIPS assembly instructions
iOpcodes = {
    '0x4' : 'beq',
    '0x5' : 'bne',
    '0x8' : 'addi',
    '0x9' : 'addiu',
    '0xa' : 'slti',
    '0xb' : 'sltiu',
    '0xc' : 'andi',
    '0xd' : 'ori',
    '0xf' : 'lui',
    '0x23' : 'lw',
    '0x24' : 'lbu',
    '0x25' : 'lhu',
    '0x28' : 'sb',
    '0x29' : 'sh',
    '0x30' : 'll',
    '0x38' : 'sc',
    '0x2b' : 'sw',
    # 17 total core I_TYPE MIPS assembly instructions
}

# Create a dictionary containing all of the 32 available registers in the MIPS ISA
# Map the register values to 5 bit length binary keys
registerDictionary = {
    '00000' : '$zero', # The constant value 0
    '00001' : '$at',   # Assembler temporary
    '00010' : '$v0',   # Values for function results and expression evaluation
    '00011' : '$v1',   # 
    '00100' : '$a0',   # Argument registers
    '00101' : '$a1',   # 
    '00110' : '$a2',   # 
    '00111' : '$a3',   # 
    '01000' : '$t0',   # Temporary registers
    '01001' : '$t1',   # 
    '01010' : '$t2',   # 
    '01011' : '$t3',   # 
    '01100' : '$t4',   # 
    '01101' : '$t5',   # 
    '01110' : '$t6',   # 
    '01111' : '$t7',   # 
    '10000' : '$s0',   # Saved (temporaries) registers
    '10001' : '$s1',   # 
    '10010' : '$s2',   # 
    '10011' : '$s3',   # 
    '10100' : '$s4',   # 
    '10101' : '$s5',   # 
    '10110' : '$s6',   # 
    '10111' : '$s7',   # 
    '11000' : '$t8',   # More Temporary registers
    '11001' : '$t9',   # 
    '11010' : '$k0',   # Registers reserved for OS kernel
    '11011' : '$k1',   # 
    '11100' : '$gp',   # Global Pointer
    '11101' : '$sp',   # Stack Pointer
    '11110' : '$fp',   # Frame Pointer
    '11111' : '$ra',   # Return Address
}

# Created a custom hex to binary lookup dictionary for ease of use
# Python bit manipulation can be tricky and this dictionary aims to 
# simplify editing binary values
hexToBinLookup = {
    '0' : '0000',
    '1' : '0001',
    '2' : '0010',
    '3' : '0011',
    '4' : '0100',
    '5' : '0101',
    '6' : '0110',
    '7' : '0111',
    '8' : '1000',
    '9' : '1001',
    'a' : '1010',
    'b' : '1011',
    'c' : '1100',
    'd' : '1101',
    'e' : '1110',
    'f' : '1111',
}

def errorOut(instruction, index):
    print("Cannot disassemble {0} at line {1}".format(instruction, index))
    sys.exit(1)  # Exit the system cleanly

def readInputFile(filename):
    """
    Function to read the input file
    --> Returns a list type (of all the hex values read in)
    """
    with open(filename, "r") as inFile:  # Auto close infile on completion
        fileLinesList = inFile.readlines()  # Read in all the lines of the file and store as a list
        return fileLinesList

def getOpCode(hexValueAsString):
    """
    Returns the (6-bit) opcode as a string
    """
    hexValSplit = hexValueAsString[:2]  # Get and store first 2 hex numbers
    hexValShifted = hex(int(hexValSplit, HEX_BASE) >> 2)  # SRL * 2
    return str(hexValShifted)  # return as string

def getRTypeFunction(hexValueAsString, index):
    """
    For R-type instructions, get the last 6 bits of the opcode as a string
    """
    bitMask = 0b00111111  # to be anded, ones in the hex places we care about
    # Get and store last two hex numbers
    hexValSplit = hexValueAsString[len(hexValueAsString)-4:]
    hexValShifted = hex(int(hexValSplit, HEX_BASE) & bitMask)

    # Guard against incorrect hex input
    if(hexValShifted not in rOpcodes.keys()):
        errorOut(hexValueAsString, index)

    return rOpcodes.get(str(hexValShifted))  # lookup in the opcode dictionary defined above

def getRTypeRDRegister(hexValueAsString, index):
    """
    RD only used in the R type functions
    R-Type = | (31-26) OP | (25-21) RS | (20-16) RT | (15-11) RD | (10-6) Shamt | (5-0) funct |
    """
    binString =  hexToBinLookup.get(hexValueAsString[4])  # 1/2 Byte 4
    binString += hexToBinLookup.get(hexValueAsString[5])  # 1/2 Byte 5

    if(binString[0:5] not in registerDictionary.keys()):
        errorOut(hexValueAsString, index)

    return registerDictionary.get(binString[0:5])

def getRSRegister(hexValueAsString, index):
    """
    Return RSregister as a string for both i and r type instructions
    R-Type = | (31-26) OP | (25-21) RS | (20-16) RT | (15-11) RD | (10-6) Shamt | (5-0) funct |
    I-Type = | (31-26) OP | (25-21) RS | (20-16) RT | (15-0) Immediate |
    """
    binString =  hexToBinLookup.get(hexValueAsString[1])  # 1/2 Byte 1
    binString += hexToBinLookup.get(hexValueAsString[2])  # 1/2 Byte 2

    if(binString[2:7] not in registerDictionary.keys()):
        errorOut(hexValueAsString, index)

    return registerDictionary.get(binString[2:7])

def getRTRegister(hexValueAsString, index):
    """
    Return RTregister as a string for both i and r type instructions
    R-Type = | (31-26) OP | (25-21) RS | (20-16) RT | (15-11) RD | (10-6) Shamt | (5-0) funct |
    I-Type = | (31-26) OP | (25-21) RS | (20-16) RT | (15-0) Immediate |
    """
    binString =  hexToBinLookup.get(hexValueAsString[2])  # 1/2 Byte 2
    binString += hexToBinLookup.get(hexValueAsString[3])  # 1/2 Byte 3

    if(binString[3:] not in registerDictionary.keys()):
        errorOut(hexValueAsString, index)

    return registerDictionary.get(binString[3:])  # Lookup 

def getRTypeShamt(hexValueAsString):
    """
    Return the shift amount (useful for shift instructions) as a string
    R-Type = | (31-26) OP | (25-21) RS | (20-16) RT | (15-11) RD | (10-6) Shamt | (5-0) funct |
    """
    binString =  hexToBinLookup.get(hexValueAsString[5])  # 1/2 Byte 5 
    binString += hexToBinLookup.get(hexValueAsString[6])  # 1/2 Byte 6
    return str(int(binString[1:6], BIN_BASE)) 

def getITypeImmediate(hexValueAsString):
    """
    Return the last 4 bytes (immediate) of the Itype instruction as a string (integer representation)
    I-Type = | (31-26) OP | (25-21) RS | (20-16) RT | (15-0) Immediate |
    """
    binString =  hexToBinLookup.get(hexValueAsString[4])  # 1/2 Byte 4  
    binString += hexToBinLookup.get(hexValueAsString[5])  # 1/2 Byte 5
    binString += hexToBinLookup.get(hexValueAsString[6])  # 1/2 Byte 6
    binString += hexToBinLookup.get(hexValueAsString[7])  # 1/2 Byte 7
    return str(int(binString, BIN_BASE))  # Return the string of bits as a string (integer representation)

def twosCM(immediate):
    """
    Takes an integer (2 bytes) and will convert it to 16 bits 2s complement
    """

    # Take the 2's complement of the binary number passed in using the process below
    binString = bin(int(immediate) & 0xFFFF).strip('0b')  # Ensure only looking at the 16 bits
    listedBinString = list(binString)  # Create a list for individual character manipulation
    for i, c in enumerate(binString):  # Iterate through the enumerated list
        if (i > 0):  # Ignore the first bit because it is the signed bit
            # Inverse the bits using the logic below
            if (c == '0'):  
                listedBinString[i] = '1' 
            elif (c == '1'):
                listedBinString[i] = '0'

    binString = ''.join(listedBinString)  # Replace the original string with the 1's complement
    twosCM = int(binString) + 1  # Add 1 to the 1's CM to get the 2's complement

    return str(twosCM)

def getSignedInteger(twosCM):
    """
    Takes a 16 bit twos complement number and turns it into a signed integer and returns it as a string
    """
    signBit = twosCM[0]

    if (signBit == '0'):  # positive
        return str(int(twosCM[1:], BIN_BASE))
    else:
        return str(int(twosCM[1:], BIN_BASE) * -1)

def main():
    hex_values = readInputFile(sys.argv[1])
    numInstructions = len(hex_values)
    #lineQ = queue.Queue(maxsize=5000)
    listQ = []  # Create an empty list to store the return results to be written to the file
    
    tempAddress = ""; checkIndex = 0

    for index, value in enumerate(hex_values):

        opcode = getOpCode(value)  # Start by getting the opcode

        if(opcode == "0x0"):  # Set as instruction type R-Type
            func = getRTypeFunction(value, index)
            rd = getRTypeRDRegister(value, index)
            rs = getRSRegister(value, index)
            rt = getRTRegister(value, index)
            sh = getRTypeShamt(value)

            if(func == 'srl' or func == 'sll'):  # Special cases for the shift functions
                msg = "\t{0}, {1}, {2}, {3}".format(func, rd, rt, sh)
                #print(msg)
                listQ.append(msg)
            else:
                msg = "\t{0}, {1}, {2}, {3}".format(func, rd, rs, rt)
                #print(msg)
                listQ.append(msg) 

        elif(opcode in iOpcodes.keys()):  # Check for iOpcodes as well
            if(opcode not in iOpcodes.keys()):
                errorOut(value, index)

            func = iOpcodes.get(opcode)
            rs = getRSRegister(value, index)
            rt = getRTRegister(value, index)
            im = getITypeImmediate(value)

            if(func == 'sw' or func == 'lw'):  # Account for the store and load word instructions
                msg = "\t{0}, {1}, {2}({3})".format(func, rt, im, rs)
                #print(msg)
                listQ.append(msg)
            elif(func == 'beq' or func == 'bne'):
                if(index == checkIndex):
                    listQ.append("Addr_{}:".format(tempAddress))
                else:
                    # Check to see if the immediate is positive or negative by checking the sign bit
                    if(int(im) >= int('1000000000000000', BIN_BASE)):  # Should be 32768
                        tcm = twosCM(im)
                        signedInt = getSignedInteger(tcm)
    
                        tempIndex = index + int(signedInt)
                        # print(int(signedInt))
                        if(tempIndex < 0):  # Check that we are not jumping to an invalid index
                            tempIndex = 0
                        
                        hexAddr = hex(tempIndex * 4).replace('0x', '').zfill(4)
                        if(listQ[tempIndex].startswith('Addr')):  # Check to see that the address has not already been placed there
                            pass
                        else: 
                            listQ.insert(tempIndex, "Addr_{}:".format(hexAddr))
                        
                        msg = "\t{0}, {1}, {2}, Addr_{3}".format(func, rt, rs, hexAddr)
                        #print(msg)
                        listQ.append(msg)
                        
                    else:  # For positive integers (already in 2's CM form)
                        checkIndex = index + int(im) 
                        tempAddress = hex((checkIndex * 4) + 4).replace('0x', '').zfill(4)
    
                        msg = "\t{0}, {1}, {2}, Addr_{3}".format(func, rt, rs, tempAddress)
                        #print(msg)
                        listQ.append(msg)

            else:  # All other I-type instructions
                msg = "\t{0}, {1}, {2}, {3}".format(func, rt, rs, im)
                #print(msg)
                listQ.append(msg)
    
    # Finally, write the entire listQ to the output file
    # print('\n')
    for item in listQ:
        print(item)

    with open("{}.s".format(str(sys.argv[1])[:str(sys.argv[1]).find('.')]), 'w+') as outFile:
        for item in listQ:
            outFile.write(item)
            outFile.write('\n')

if __name__ == '__main__':
    main()


