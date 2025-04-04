import os
import sys

# Instruction type definitions
RType = ["0110011"]
RTypeFunct3 = {
    "000": ["add", "sub"],  # depends on funct7
    "101": "srl",
    "111": "and",
    "010": "slt",
    "110": "or"
}
IType = {"0000011": "lw", "0010011": "addi", "1100111": "jalr"}
SType = {"0100011": "sw"}
BType = ["1100011"]
BTypeFunct3 = {"000": "beq", "001": "bne"}
JType = {"1101111": "jal"}

HaltInst = "00000000000000000000000001100011"

# Memory configuration (data memory only)
MemStart = 0x00010000
MemSize = 32

# Global variables
r = {}
Memory = []

def ResetSimulator():
    """Reset all registers and memory to initial state"""
    global r, Memory
    # Initialize 32 registers as 32-bit zero strings.
    r = {f"x{i}": "0" * 32 for i in range(32)}
    # x2 is the stack pointer; initialize to 380.
    r["x2"] = f"{380:032b}"
    # Data memory: 32 words (128 bytes)
    Memory = ["0" * 32 for _ in range(MemSize)]

def ConvertToBinary(n, bits=32, flag=False):
    """Convert number to binary string of specified length"""
    if flag and n < 0:
        n = (1 << bits) + n
    return f"{n & ((1 << bits) - 1):0{bits}b}"

def BinaryToDecimal(bstr):
    """Convert binary string to signed decimal"""
    if bstr[0] == "0":
        return int(bstr, 2)
    else:
        return int(bstr, 2) - (1 << len(bstr))

def CheckType(Opcode):
    """Determine instruction type from opcode"""
    if Opcode in RType:
        return "R"
    elif Opcode in IType:
        return "I"
    elif Opcode in SType:
        return "S"
    elif Opcode in BType:
        return "B"
    elif Opcode in JType:
        return "J"
    return "invalid"

def ExecuteInstruction(BinaryInst, PC):
    """Execute a single instruction and return updated PC (and halt signal)"""
    if len(BinaryInst) != 32:
        raise ValueError("Instruction must be 32 bits long.")

    if BinaryInst == HaltInst:
        return True, PC  # Halt signal

    # Extract instruction fields
    Funct7 = BinaryInst[0:7]
    rs2Bin = BinaryInst[7:12]
    rs1Bin = BinaryInst[12:17]
    funct3 = BinaryInst[17:20]
    rdBin = BinaryInst[20:25]
    Opcode = BinaryInst[25:32]

    rd = int(rdBin, 2)
    rs1 = int(rs1Bin, 2)
    rs2 = int(rs2Bin, 2)
    InstrType = CheckType(Opcode)

    if InstrType == "R":
        rs1Val = BinaryToDecimal(r[f"x{rs1}"])
        rs2Val = BinaryToDecimal(r[f"x{rs2}"])
        if funct3 == "000":
            if Funct7 == "0000000":
                x = rs1Val + rs2Val  # ADD
            else:
                x = rs1Val - rs2Val  # SUB
        elif funct3 == "010":
            x = 1 if rs1Val < rs2Val else 0  # SLT
        elif funct3 == "101":
            x = rs1Val >> (rs2Val & 0x1F)  # SRL
        elif funct3 == "111":
            x = rs1Val & rs2Val  # AND
        elif funct3 == "110":
            x = rs1Val | rs2Val  # OR
        else:
            x = 0
        r[f"x{rd}"] = ConvertToBinary(x)
        PC += 4

    elif InstrType == "I":
        immBin = BinaryInst[0:12]
        immVal = BinaryToDecimal(immBin)
        rs1Val = BinaryToDecimal(r[f"x{rs1}"])
        o = IType[Opcode]
        if o == "addi":
            x = rs1Val + immVal
            r[f"x{rd}"] = ConvertToBinary(x)
            PC += 4
        elif o == "jalr":
            if rd != 0:
                r[f"x{rd}"] = ConvertToBinary(PC + 4)
            PC = (rs1Val + immVal) & ~1
        elif o == "lw":
            Address = rs1Val + immVal
            index = (Address - MemStart) // 4
            if 0 <= index < MemSize and Address % 4 == 0:
                r[f"x{rd}"] = Memory[index]
            else:
                r[f"x{rd}"] = "0" * 32
            PC += 4

    elif InstrType == "S":
        immBin = BinaryInst[0:7] + BinaryInst[20:25]
        immVal = BinaryToDecimal(immBin)
        rs1Val = BinaryToDecimal(r[f"x{rs1}"])
        rs2Val = BinaryToDecimal(r[f"x{rs2}"])
        if SType[Opcode] == "sw":
            Address = rs1Val + immVal
            index = (Address - MemStart) // 4
            if 0 <= index < MemSize and Address % 4 == 0:
                Memory[index] = r[f"x{rs2}"]
        PC += 4

    elif InstrType == "B":
        immBits = BinaryInst[0] + BinaryInst[24] + BinaryInst[1:7] + BinaryInst[20:24] + "0"
        immVal = BinaryToDecimal(immBits)
        rs1Val = BinaryToDecimal(r[f"x{rs1}"])
        rs2Val = BinaryToDecimal(r[f"x{rs2}"])
        BranchOp = BTypeFunct3.get(funct3, None)
        if BranchOp == "beq" and rs1Val == rs2Val:
            PC += immVal
        elif BranchOp == "bne" and rs1Val != rs2Val:
            PC += immVal
        else:
            PC += 4

    elif InstrType == "J":
        immStr = BinaryInst[0] + BinaryInst[12:20] + BinaryInst[11] + BinaryInst[1:11] + "0"
        immVal = BinaryToDecimal(immStr)
        if rd != 0:
            r[f"x{rd}"] = ConvertToBinary(PC + 4)
        PC += immVal

    else:
        PC += 4  # Unknown instruction

    return False, PC

def GetRegisterDump(PC):
    """Generate register dump string"""
    Dump = "0b" + ConvertToBinary(PC)
    for i in range(32):
        Dump += " " + "0b" + r[f"x{i}"]
    return Dump

def GetMemoryTrace():
    """Generate memory trace string for data memory only"""
    trace = []
    for i in range(MemSize):
        Address = MemStart + i * 4
        addrHex = f"0x{Address:08X}"
        trace.append(addrHex + ":0b" + Memory[i])
    return trace

def AutomatedTesting():
    """Run automated tests from input files"""
    # Directories (assumed to already exist on your system)
    Input = os.path.join("automatedTesting", "tests", "bin", "simple")
    Output = os.path.join("automatedTesting", "tests", "user_traces", "simple")

    for i in range(1, 11):
        input_file = os.path.join(Input, f"simple_{i}.txt")
        output_file = os.path.join(Output, f"simple_{i}.txt")

        # Skip if input file doesn't exist
        if not os.path.exists(input_file):
            continue

        ResetSimulator()

        # Read input instructions
        with open(input_file, "r") as infile:
            Instructions = [line.strip() for line in infile if line.strip()]

        results = []
        PC = 0
        while 0 <= PC // 4 < len(Instructions):
            instruction = Instructions[PC // 4]
            Halt, PC = ExecuteInstruction(instruction, PC)
            results.append(GetRegisterDump(PC))
            if Halt:
                break

        memTrace = GetMemoryTrace()

        # Write output without any extra blank line between sections
        with open(output_file, "w") as outfile:
            for result in results:
                outfile.write(result + "\n")
            for mem in memTrace:
                outfile.write(mem + "\n")

if __name__ == "__main__":
    AutomatedTesting()