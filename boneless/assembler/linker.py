" section linker"
"""
    registers - 1..8
    .stacks
    .heap
    .data 
    .text  
    end of memory
"""

from fixture import CodeSection

class Linker:
    order = [".data",".text"]

    def __init__(self,assem):
        print("WHAAAAT! no linker")
        print(assem) 
        # pass down the entire assembler
        self.assem = assem
        self.sections = assem.sections
    
    def link(self):
        print("Activate the LINK-O-TRON")
        for i,j in self.sections.items():
            print(i,j)
            
        
        
