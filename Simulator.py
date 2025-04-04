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

# Memory configuration
MemStart = 0x00010000
MemSize = 32
StackBase = 0x00000100
StackSize = 32

# Global variables
r = {}
Memory = []
Stack = []

def ResetSimulator():
    """Reset all registers and memory to initial state"""
    global r, Memory, Stack
    r = {f"x{i}": "0" * 32 for i in range(32)}
    r["x2"] = f"{StackBase + StackSize*4 - 4:032b}"  # Initialize stack pointer
    Memory = ["0" * 32 for _ in range(MemSize)]
    Stack = ["0" * 32 for _ in range(StackSize)]

def ConvertToBinary(n, bits=32, signed=False):
    """Convert number to binary string of specified length"""
    if signed and n < 0:
        n = (1 << bits) + n
    return f"{n & ((1 << bits) - 1):0{bits}b}"

def BinaryToDecimal(bstr):
    """Convert binary string to signed decimal"""
    if bstr[0] == "0":
        return int(bstr, 2)
    return int(bstr, 2) - (1 << len(bstr))

def CheckType(opcode):
    """Determine instruction type from opcode"""
    if opcode in RType: return "R"
    if opcode in IType: return "I"
    if opcode in SType: return "S"
    if opcode in BType: return "B"
    if opcode in JType: return "J"
    return "invalid"

def ExecuteInstruction(instr, pc):
    """Execute a single instruction and return updated pc and halt status"""
    if instr == HaltInst:
        return True, pc

    funct7 = instr[0:7]
    rs2 = int(instr[7:12], 2)
    rs1 = int(instr[12:17], 2)
    funct3 = instr[17:20]
    rd = int(instr[20:25], 2)
    opcode = instr[25:32]
    instr_type = CheckType(opcode)

    rs1_val = BinaryToDecimal(r[f"x{rs1}"])
    if instr_type in ["R", "S", "B"]:
        rs2_val = BinaryToDecimal(r[f"x{rs2}"])

    if instr_type == "R":
        if funct3 == "000":
            res = rs1_val + rs2_val if funct7 == "0000000" else rs1_val - rs2_val
        elif funct3 == "010": res = 1 if rs1_val < rs2_val else 0
        elif funct3 == "101": res = rs1_val >> (rs2_val & 0x1F)
        elif funct3 == "110": res = rs1_val | rs2_val
        elif funct3 == "111": res = rs1_val & rs2_val
        else: res = 0
        r[f"x{rd}"] = ConvertToBinary(res)
        pc += 4

    elif instr_type == "I":
        imm = BinaryToDecimal(instr[0:12])
        if IType[opcode] == "addi":
            r[f"x{rd}"] = ConvertToBinary(rs1_val + imm)
            pc += 4
        elif IType[opcode] == "jalr":
            if rd != 0:
                r[f"x{rd}"] = ConvertToBinary(pc + 4)
            pc = (rs1_val + imm) & ~1
        elif IType[opcode] == "lw":
            addr = rs1_val + imm
            if StackBase <= addr < StackBase + StackSize*4:
                r[f"x{rd}"] = Stack[(addr - StackBase)//4]
            elif MemStart <= addr < MemStart + MemSize*4:
                r[f"x{rd}"] = Memory[(addr - MemStart)//4]
            else:
                r[f"x{rd}"] = "0"*32
            pc += 4

    elif instr_type == "S":
        imm = BinaryToDecimal(instr[0:7] + instr[20:25])
        addr = rs1_val + imm
        if StackBase <= addr < StackBase + StackSize*4:
            Stack[(addr - StackBase)//4] = r[f"x{rs2}"]
        elif MemStart <= addr < MemStart + MemSize*4:
            Memory[(addr - MemStart)//4] = r[f"x{rs2}"]
        pc += 4

    elif instr_type == "B":
        imm = BinaryToDecimal(instr[0] + instr[24] + instr[1:7] + instr[20:24] + "0")
        if (funct3 == "000" and rs1_val == rs2_val) or \
           (funct3 == "001" and rs1_val != rs2_val):
            pc += imm
        else:
            pc += 4

    elif instr_type == "J":
        imm = BinaryToDecimal(instr[0] + instr[12:20] + instr[11] + instr[1:11] + "0")
        if rd != 0:
            r[f"x{rd}"] = ConvertToBinary(pc + 4)
        pc += imm

    else:
        pc += 4

    return False, pc

def GetRegisterDump(pc):
    """Generate register dump string"""
    dump = f"0b{ConvertToBinary(pc)}"
    for i in range(32):
        dump += f" 0b{r[f'x{i}']}"
    return dump

def GetMemoryTrace():
    """Generate memory trace string"""
    trace = []
    for i in range(MemSize):
        addr = MemStart + i*4
        trace.append(f"0x{addr:08X}:0b{Memory[i]}")
    return trace

def RunSimulation(input_file, output_file):
    """Run simulation for a single input file"""
    ResetSimulator()
    
    with open(input_file, "r") as f:
        instructions = [line.strip() for line in f if line.strip()]

    pc = 0
    register_dumps = []
    
    while 0 <= pc//4 < len(instructions):
        instr = instructions[pc//4]
        halt, pc = ExecuteInstruction(instr, pc)
        register_dumps.append(GetRegisterDump(pc))
        if halt:
            break

    memory_trace = GetMemoryTrace()

    with open(output_file, "w") as f:
        f.write("\n".join(register_dumps) + "\n")
        f.write("\n".join(memory_trace) + "\n")

def AutomatedTesting():
    """Run automated tests for all input files"""
    base_path = r"C:\Users\bimal\OneDrive\Desktop\final_valuation_framework_mar30_2025_students_v5"
    input_dir = os.path.join(base_path, "automatedTesting", "tests", "bin", "simple")
    output_dir = os.path.join(base_path, "automatedTesting", "tests", "user_traces", "simple")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    for i in range(1, 11):
        input_file = os.path.join(input_dir, f"simple_{i}.txt")
        output_file = os.path.join(output_dir, f"simple_{i}.txt")
        
        if os.path.exists(input_file):
            try:
                RunSimulation(input_file, output_file)
                print(f"Processed: {input_file} -> {output_file}")
            except Exception as e:
                print(f"Error processing {input_file}: {str(e)}")
        else:
            print(f"Input file not found: {input_file}")

if __name__ == "__main__":
    AutomatedTesting()