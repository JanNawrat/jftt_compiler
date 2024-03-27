class Variable:
    def __init__(self, location):
        self.location = location
        self.initialized = False

    def __repr__(self):
        return f'Type: variable, Initialized: {"True" if self.initialized else "False"}, Location: {self.location}'

class Array:
    def __init__(self, name, location, size):
        self.name = name
        self.location = location
        self.size = size

    def __repr__(self):
        return f'Type: array, Location: {self.location}, Size: {self.size}'

    def get(self, index):
        if 0 <= index <=  self.size - 1:
            return self.location + index
        else:
            raise Exception(f'Index {index} is out of bounds for array {self.name}')
        
class Pointer:
    def __init__(self, location, type):
        self.location = location
        self.type = type

    def __repr__(self):
        return f'Type: {self.type}, Location: {self.location}'
        
class Memory(dict):
    def __init__(self, offset):
        super().__init__()
        self.offset = offset

    def add_variable(self, name):
        if name in self:
            raise Exception(f'variable {name} already declared')
        self.setdefault(name, Variable(self.offset))
        self.offset += 1

    def add_array(self, name, size):
        if name in self:
            raise Exception(f'array {name} already declared')
        elif size == 0:
            raise Exception(f'array {name} cannot be declared with size 0')
        self.setdefault(name, Array(name, self.offset, size))
        self.offset += size

    def add_pointer(self, name, type):
        if name in self:
            raise Exception(f'Pointer {name} already declared')
        self.setdefault(name, Pointer(self.offset, type))
        self.offset += 1

    def is_pointer(self, name):
        if name in self:
            if not isinstance(self[name], Pointer):
                return False
            if self[name].type != 'variable':
                raise Exception(f'Pointer {name} points to an array')
            return True
        else:
            raise Exception(f'Variable {name} is undeclared')
        
    def is_array_pointer(self, name):
        if name in self:
            if not isinstance(self[name], Pointer):
                return False
            if self[name].type != 'array':
                raise Exception(f'Pointer {name} points to a variable')
            return True
        else:
            raise Exception(f'Array {name} is undeclared')
        
    def get_type(self, name):
        if name in self:
            if isinstance(self[name], Variable):
                return 'variable'
            if isinstance(self[name], Array):
                return 'array'
            if isinstance(self[name], Pointer):
                return 'pointer'
        else:
            raise Exception(f'{name} is undeclared')
        
    def get_pointer_type(self, name):
        if name in self:
            if not isinstance(self[name], Pointer):
                raise Exception(f'{name} is not a pointer')
            return self[name].type
        else:
            raise Exception(f'Pointer {name} is undeclared')

    def get_variable(self, name):
        if name in self:
            return self[name].location
        else:
            raise Exception(f'Variable {name} is undeclared')
        
    def get_array_at_index(self, name, index):
        if name in self:
            a = self[name]
            if isinstance(a, Array):
                return a.get(index)
            else:
                raise Exception(f'{name} is not an array')
        else:
            raise Exception(f'Array {name} is undeclared')
        
class Procedure:
    def __init__(self, name, location, callback):
        self.name = name
        self.pointers = []
        self.location = location
        self.callback = callback
    
    def add_pointer(self, location, type):
        self.pointers.append(Pointer(location, type))

    def __repr__(self):
        return f'Procedure: {self.name}, location: {self.location}'

        
class Generator:
    def __init__(self):
        self.debug = True
        self.offset = 0
        self.memory = None
        self.procedures = dict()
        self.code = []
        self.errorMode = False
        self.loopDepth = 0
        self.lineno = 1

    def gen_procedure(self, head, declarations, commands):
        name = head[0]
        args = head[1]
        if name in self.procedures:
            print(f'Error: Line {head[2]}: procedure {name} already declared')
            return
        if len(self.code) == 0:
            self.code.append('PLACEHOLDER')
        procedure = Procedure(name, len(self.code), self.offset)
        self.memory = Memory(self.offset + 1)

        # gen pointers
        for arg in args:
            self.memory.add_pointer(arg[1], arg[0])
            procedure.add_pointer(self.memory.get_variable(arg[1]), arg[0])
        
        self.gen_declarations(declarations)
        self.gen_body(commands)
        self.procedures.setdefault(name, procedure)
        self.offset = self.memory.offset

        # return
        self.gen_number(procedure.callback, 'a')
        self.code.append('LOAD a')
        self.code.append('INC a')
        self.code.append('INC a')
        self.code.append('INC a')
        self.code.append('JUMPR a')

    def gen(self, declarations, commands):
        if len(self.code) > 0:
            self.code[0] = f'JUMP {len(self.code)}'
        # for procedure in self.procedures:
            # print(procedure)
        self.memory = Memory(self.offset)
        self.gen_declarations(declarations)
        self.gen_body(commands)
        self.code.append("HALT")

    def gen_declarations(self, declarations):
        for declaration in declarations:
            if declaration[0] == "variable":
                try:
                    self.memory.add_variable(declaration[1])
                except Exception as e:
                    print(f'Error: Line {declaration[2]}: {e}')
                    self.errorMode = True
            else: # declaration[0] == "array"
                try:
                    self.memory.add_array(declaration[1], declaration[2])
                except Exception as e:
                    print(f'Error: Line {declaration[3]}: {e}')
                    self.errorMode = True
        # for name, entry in self.memory.items():
            # print(f'Name: {name}, {entry}')

    def gen_body(self, commands):
        for command in commands:
            # print(f"Generating command: {command}")
            if command[0] == 'assign':
                target = command[1]
                expression = command[2]
                primary_reg = 'h'
                self.lineno = command[3]
                try:
                    self.load_address(target, primary_reg)
                    self.calculate_expression(expression, command[3])
                    self.code.append(f'STORE {primary_reg}')
                except Exception as e:
                    print(f'Error: Line {command[3]}: {e}')
                    self.errorMode = True

                self.initialize(target)
            
            elif command[0] == 'write':
                target = command[1]
                if target[0] == 'number':
                    self.gen_number(target[1])
                    self.code.append('WRITE')
                else: # target[0] == 'load'
                    self.lineno = command[2]
                    primary_reg = 'h'
                    try:
                        self.load_address(target[1], primary_reg)
                        self.code.append(f'LOAD {primary_reg}')
                        self.code.append('WRITE')
                    except Exception as e:
                        print(f'Error: Line {command[2]}: {e}')
                        self.errorMode = True

            elif command[0] == 'read':
                target = command[1]
                primary_reg = 'h'
                self.lineno = command[2]
                try:
                    self.load_address(target, primary_reg)
                    self.code.append('READ')
                    self.code.append(f'STORE {primary_reg}')
                except Exception as e:
                    print(f'Error Line: {command[2]}: {e}')
                    self.errorMode = True

                self.initialize(target)

            elif command[0] == 'ifelse':
                # TODO: optimize for numbers
                condition = command[1]
                # print(f'Condition: {condition}')
                (condition, swap) = self.simplify_condition(condition)
                # print(f'Simplified: {(condition, swap)}')

                if not swap:
                    block_a = command[2]
                    block_b = command[3]
                else:
                    block_b = command[2]
                    block_a = command[3]

                # print(f'Block A: {block_a}')
                # print(f'Block B: {block_b}')
                
                self.generate_condition(condition)

                before_block_a = len(self.code)
                self.code.append('JUMP to block_b')

                self.gen_body(block_a)

                after_block_a = len(self.code)
                self.code.append('JUMP to block_b_end')

                self.gen_body(block_b)

                after_block_b = len(self.code)
                self.code[before_block_a] = f'JUMP {after_block_a + 1}'
                self.code[after_block_a] = f'JUMP {after_block_b}'

            elif command[0] == 'while':
                # TODO: optimize for numbers
                condition = command[1]
                block = command[2]
                # print(f'Condition: {condition}')
                (condition, swap) = self.simplify_condition(condition)
                # print(f'Simplified: {(condition, swap)}')
                # print(f'Block: {block}')
                
                before_condition = len(self.code)
                self.generate_condition(condition)

                if not swap:
                    before_block = len(self.code)
                    self.code.append('JUMP to block end')
                    self.loopDepth += 1
                    self.gen_body(block)
                    self.loopDepth -= 1
                    self.code.append(f'JUMP {before_condition}')
                    after_block = len(self.code)
                    self.code[before_block] = f'JUMP {after_block}'
                else: # swap
                    before_block = len(self.code) - 1
                    self.loopDepth += 1
                    self.gen_body(block)
                    self.loopDepth -= 1
                    self.code.append(f'JUMP {before_condition}')
                    after_block = len(self.code)
                    if condition[0] == 'gt':
                        self.code[before_block] = f'JPOS {after_block}'
                    else: # condition[0] =='eq'
                        self.code[before_block] = f'JZERO {after_block}'

            elif command[0] == 'repeat':
                # TODO: optimize for numbers
                condition = command[1]
                block = command[2]
                # print(f'Condition: {condition}')
                (condition, swap) = self.simplify_condition(condition)
                # print(f'Simplified: {(condition, swap)}')
                # print(f'Block: {block}')

                block_start = len(self.code)
                self.loopDepth += 1
                self.gen_body(block)
                self.loopDepth -= 1
                
                self.generate_condition(condition)
                if not swap:
                    self.code.append(f'JUMP {block_start}')
                else: # swap
                    last_jump = len(self.code) - 1
                    if condition[0] == 'gt':
                        self.code[last_jump] = (f'JPOS {block_start}')
                    else: # condition[0] = 'eq'
                        self.code[last_jump] = (f'JZERO {block_start}')

            elif command[0] == 'call':
                name = command[1][0]
                args = command[1][1]
                lineno = command[1][2]

                for arg in args:
                    try:
                        type = self.memory.get_type(arg)
                        self.initialize((type, arg))
                    except:
                        pass

                if not name in self.procedures:
                    print(f'Error: Line {lineno}: procedure {name} not declared (this may mean that recursive call was issued)')
                    self.errorMode = True
                    continue
                procedure = self.procedures[name]
                if len(args) != len(procedure.pointers):
                    print(f'Error: Line {lineno}: argument count mismatch with procedure {name} (received: {len(args)}, expected: {len(procedure.pointers)})')
                    self.errorMode = True
                    continue
                for i in range(len(args)):
                    type = self.memory.get_type(args[i])
                    if type == 'pointer':
                        type = self.memory.get_pointer_type(args[i])
                    
                    if type != procedure.pointers[i].type:
                        print(f'Error: Line {lineno}: argument type mismatch with procedure {name}')
                        self.errorMode = True
                        continue
                    
                    # fix assigning pointer arrays
                    if type == 'variable':
                        self.load_address((type, args[i]), 'h')
                    else: # type == 'array'
                        self.load_address((type, args[i], ('number', 0)), 'h')

                    self.code.append('GET h')
                    self.gen_number(procedure.pointers[i].location, 'b')
                    self.code.append('STORE b')
                
                # saving location for return
                self.gen_number(procedure.callback, 'b')
                self.code.append('STRK a')
                self.code.append('STORE b')
                self.code.append(f'JUMP {procedure.location}')

    def perform_mulitplication(self, second_reg = 'b', third_reg = 'c', fourth_reg = 'd'):
        self.code.append(f'RST {second_reg}')
        # multiply
        self.code.append(f'GET {fourth_reg}')
        k = len(self.code)
        self.code.append(f'JZERO {k + 11}')
        self.code.append(f'SHR {fourth_reg}')
        self.code.append(f'SHL {fourth_reg}')
        self.code.append(f'SUB {fourth_reg}')
        k = len(self.code)
        self.code.append(f'JZERO {k + 4}')
        self.code.append(f'GET {second_reg}')
        self.code.append(f'ADD {third_reg}')
        self.code.append(f'PUT {second_reg}')
        # shift
        self.code.append(f'SHL {third_reg}')
        self.code.append(f'SHR {fourth_reg}')
        k = len(self.code)
        self.code.append(f'JUMP {k - 11}')
        # done
        self.code.append(f'GET {second_reg}')

    def perform_division(self, result = 'b', counter = 'c', partial = 'd', remainder = 'e', divisor = 'f'):
        self.code.append(f'RST {result}')

        # cannot divide by zero
        self.code.append(f'GET {divisor}')
        k = len(self.code)
        self.code.append(f'JPOS {k + 2}')
        k = len(self.code)
        self.code.append(f'JUMP {k + 22}')

        # check exit condition
        self.code.append(f'GET {divisor}')
        self.code.append(f'SUB {remainder}')
        k = len(self.code)
        self.code.append(f'JPOS {k + 19}')

        # setup
        self.code.append(f'RST {counter}')
        self.code.append(f'INC {counter}')
        self.code.append(f'GET {divisor}')
        self.code.append(f'PUT {partial}')
        # loop start
        self.code.append(f'SHL {partial}')

        # check for end loop
        self.code.append(f'GET {partial}')
        self.code.append(f'SUB {remainder}')
        k = len(self.code)
        self.code.append(f'JPOS {k + 3}')

        self.code.append(f'SHL {counter}')
        k = len(self.code)
        self.code.append(f'JUMP {k - 5}')

        # end loop
        self.code.append(f'SHR {partial}')
        self.code.append(f'GET {remainder}')
        self.code.append(f'SUB {partial}')
        self.code.append(f'PUT {remainder}')
        self.code.append(f'GET {result}')
        self.code.append(f'ADD {counter}')
        self.code.append(f'PUT {result}')
        k = len(self.code)
        self.code.append(f'JUMP {k - 20}')


    def generate_condition(self, condition):
        operator = condition[0]
        first_value = condition[1]
        second_value = condition[2]

        # first value goes to e
        first_value_reg = 'e'
        # second value goes to f
        second_value_reg = 'f'

        third_reg = 'b'

        if first_value[0] == 'number':
            self.gen_number(first_value[1], first_value_reg)
        else: #first_value[0] == 'load'
            self.load_address(first_value[1], first_value_reg)
            self.code.append(f'LOAD {first_value_reg}')
            self.code.append(f'PUT {first_value_reg}')
        
        if second_value[0] == 'number':
            self.gen_number(second_value[1], second_value_reg)
        else: #second_value[0] == 'load'
            self.load_address(second_value[1], second_value_reg)
            self.code.append(f'LOAD {second_value_reg}')
            self.code.append(f'PUT {second_value_reg}')
        
        if operator == 'gt':
            self.code.append(f'GET {first_value_reg}')
            self.code.append(f'SUB {second_value_reg}')
            k = len(self.code)
            self.code.append(f'JPOS {k + 2}')
        
        else: # operator == 'eq'
            self.code.append(f'GET {first_value_reg}')
            self.code.append(f'SUB {second_value_reg}')
            self.code.append(f'PUT {third_reg}')
            self.code.append(f'GET {second_value_reg}')
            self.code.append(f'SUB {first_value_reg}')
            self.code.append(f'ADD {third_reg}')
            k = len(self.code)
            self.code.append(f'JZERO {k + 2}')
            

    def simplify_condition(self, condition):
        operator = condition[0]
        first_value = condition[1]
        second_value = condition[2]


        if operator == 'eq':
            return condition, False
        elif operator == 'neq':
            return ('eq', first_value, second_value), True
        elif operator == 'gt':
            return condition, False
        elif operator == 'lt':
            return ('gt', second_value, first_value), False
        elif operator == 'geq':
            return ('gt', second_value, first_value), True
        else: # operator == 'leq'
            return ('gt', first_value, second_value), True

    def calculate_expression(self, expression, lineno):
        # single argument expressions:
        if expression[0] == 'load' and self.notInitialized(expression[1]):
            if self.loopDepth == 0:
                print(f'Error: Line {lineno}: variable {expression[1][1]} not initialized')
                self.errorMode = True
            else:
                print(f'Warning: Line {lineno}: variable {expression[1][1]} may be not initialized')
        
        if expression[0] == "number":
            self.gen_number(expression[1], 'a')

        elif expression[0] == "load":
            primary_reg = 'f';
            self.load_address(expression[1], primary_reg)
            self.code.append(f'LOAD {primary_reg}')
        
        # double argument expressions:
        else:
            operation = expression[0]
            first_arg = expression[1]
            second_arg = expression[2]

            if first_arg[0] == 'load' and self.notInitialized(first_arg[1]):
                if self.loopDepth == 0:
                    print(f'Error: Line {lineno}: variable {first_arg[1][1]} not initialized')
                    self.errorMode = True
                else:
                    print(f'Warning: Line {lineno}: variable {first_arg[1][1]} may be not initialized')

            if second_arg[0] == 'load' and self.notInitialized(second_arg[1]):
                if self.loopDepth == 0:
                    print(f'Error: Line {lineno}: variable {second_arg[1][1]} not initialized')
                    self.errorMode = True
                else:
                    print(f'Warning: Line {lineno}: variable {second_arg[1][1]} may be not initialized')

            # two numbers
            if first_arg[0] == 'number' and second_arg[0] == 'number':
                if operation == 'add':
                    result = first_arg[1] + second_arg[1]
                elif operation == 'sub':
                    result = max(0, first_arg[1] - second_arg[1])
                elif operation == 'mul':
                    result = first_arg[1] * second_arg[1]
                elif operation == 'div':
                    result = first_arg[1] // second_arg[1]
                else: # operation == 'mod:
                    result = first_arg[1] % second_arg[1]
                self.gen_number(result, 'a')

            # at least one variable/array
            else:
                first_value_reg = 'f'
                second_value_reg = 'g'

                # special cases
                if (first_arg[0] == 'number' and second_arg[0] == 'load') or (first_arg[0] == 'load' and second_arg[0] == 'number'):
                    if first_arg[0] == 'number':
                        num_arg = first_arg
                        var_arg = second_arg
                    else:
                        num_arg = second_arg
                        var_arg = first_arg

                        # efficient decrement
                        if num_arg[1] == 1 and operation == 'sub':
                            self.load_address(var_arg[1], first_value_reg)
                            self.code.append(f'LOAD {first_value_reg}')
                            self.code.append('DEC a')
                            return
                        
                        # efficient division by 2
                        if num_arg[1] == 2 and operation == 'div':
                            self.load_address(var_arg[1], first_value_reg)
                            self.code.append(f'LOAD {first_value_reg}')
                            self.code.append('SHR a')
                            return
                    
                    # efficient increment
                    if num_arg[1] == 1 and operation == 'add':
                        self.load_address(var_arg[1], first_value_reg)
                        self.code.append(f'LOAD {first_value_reg}')
                        self.code.append('INC a')
                        return
                    
                    # efficient multiplication by 2
                    if num_arg[1] == 2 and operation == 'mul':
                        self.load_address(var_arg[1], first_value_reg)
                        self.code.append(f'LOAD {first_value_reg}')
                        self.code.append('SHL a')
                        return

                # load first value
                if first_arg[0] == 'number':
                    self.gen_number(first_arg[1], first_value_reg)
                else: #first_arg[0] == 'load'
                    self.load_address(first_arg[1], first_value_reg)
                    self.code.append(f'LOAD {first_value_reg}')
                    self.code.append(f'PUT {first_value_reg}')

                # load second value
                if second_arg[0] == 'number':
                    self.gen_number(second_arg[1], second_value_reg)
                else: #second_arg[0] == 'load'
                    self.load_address(second_arg[1], second_value_reg)
                    self.code.append(f'LOAD {second_value_reg}')
                    self.code.append(f'PUT {second_value_reg}')

                if operation == 'add':
                    self.code.append(f'GET {first_value_reg}')
                    self.code.append(f'ADD {second_value_reg}')
                
                elif operation == 'sub':
                    self.code.append(f'GET {first_value_reg}')
                    self.code.append(f'SUB {second_value_reg}')

                # TODO: optimize consts
                elif operation == 'mul':
                    self.perform_mulitplication(third_reg=first_value_reg, fourth_reg=second_value_reg)

                # TODO: optimize consts
                else: # operation == 'div' or operation == 'mod'
                    secondary_reg = 'b'
                    self.perform_division(remainder=first_value_reg, divisor=second_value_reg)

                    if operation == 'div':
                        self.code.append(f'GET {secondary_reg}')
                    else: # operation == 'mod'
                        self.code.append(f'GET {first_value_reg}')

    def gen_number(self, number, reg = 'a'):
        self.code.append(f'RST {reg}')
        if number == 0:
            return
        binary = bin(number)[2:]
        for bit in binary[:-1]:
            if bit == '1':
                self.code.append(f'INC {reg}')
            self.code.append(f'SHL {reg}')
        if binary[-1] == '1':
            self.code.append(f'INC {reg}')

    # # will use a, if array[var]
    # def load_address(self, memory_cell, primary_reg):
    #     secondary_reg = 'a'
    #     if memory_cell[0] == 'variable':
    #         address = self.memory.get_variable(memory_cell[1])
    #         self.gen_number(address, primary_reg)
    #     else: # memory_cell[0] == 'array'
    #         index = memory_cell[2]
    #         if index[0] == 'number':
    #             address = self.memory.get_array_at_index(memory_cell[1], index[1])
    #             self.gen_number(address, primary_reg)
    #         else: # index[0] == 'load'
    #             address = self.memory.get_array_at_index(memory_cell[1], 0)
    #             secondary_address = self.memory.get_variable(index[1])
    #             self.gen_number(secondary_address, secondary_reg)
    #             self.code.append(f'LOAD {secondary_reg}')
    #             self.gen_number(address, primary_reg)
    #             self.code.append(f'ADD {primary_reg}')
    #             self.code.append(f'PUT {primary_reg}')
            
    # will use a, if array[var]
    # will use a, if pointers are used
    def load_address(self, memory_cell, primary_reg):
        secondary_reg = 'a'
        if memory_cell[0] == 'variable':
            address = self.memory.get_variable(memory_cell[1])
            self.gen_number(address, primary_reg)

            if isinstance(self.memory[memory_cell[1]], Array):
                raise Exception(f'{memory_cell[1]} is an array')

            # handling pointers
            if self.memory.is_pointer(memory_cell[1]):
                self.code.append(f'LOAD {primary_reg}')
                self.code.append(f'PUT {primary_reg}')

        else: # memory_cell[0] == 'array'
            index = memory_cell[2]

            if index[0] == 'load':
                var = index[1]
                if var in self.memory and isinstance(self.memory[var], Variable) and not self.memory[var].initialized:
                    if self.loopDepth == 0:
                        print(f'Error: Line {self.lineno}: variable {var} not initialized')
                        self.errorMode = True
                    else:
                        print(f'Warning: Line {self.lineno}: variable {var} may be not initialized')

            # handling pointers
            if self.memory.is_array_pointer(memory_cell[1]):
                address = self.memory.get_variable(memory_cell[1])

                if index[0] == 'number':
                    self.gen_number(address, primary_reg)
                    self.code.append(f'LOAD {primary_reg}')
                    self.gen_number(index[1], primary_reg)
                    self.code.append(f'ADD {primary_reg}')
                    self.code.append(f'PUT {primary_reg}')

                else: # index[0] == 'load'
                    self.gen_number(address, primary_reg)
                    self.code.append(f'LOAD {primary_reg}')
                    self.code.append(f'PUT {primary_reg}')
                    secondary_address = self.memory.get_variable(index[1])
                    self.gen_number(secondary_address, 'a')

                    # handling pointers... again
                    if self.memory.is_pointer(index[1]):
                        self.code.append(f'LOAD a')
                        self.code.append(f'LOAD a')
                        self.code.append(f'ADD {primary_reg}')
                        self.code.append(f'PUT {primary_reg}')

                    # handling non pointers
                    else:
                        self.code.append(f'LOAD a')
                        self.code.append(f'ADD {primary_reg}')
                        self.code.append(f'PUT {primary_reg}')


            # handling non pointers
            else:
                if index[0] == 'number':
                    address = self.memory.get_array_at_index(memory_cell[1], index[1])
                    self.gen_number(address, primary_reg)
                else: # index[0] == 'load'

                    # once again handling pointers
                    if self.memory.is_pointer(index[1]):
                        address = self.memory.get_array_at_index(memory_cell[1], 0)
                        secondary_address = self.memory.get_variable(index[1])
                        self.gen_number(secondary_address, 'a')
                        self.code.append(f'LOAD a')
                        self.code.append(f'LOAD a')
                        self.gen_number(address, primary_reg)
                        self.code.append(f'ADD {primary_reg}')
                        self.code.append(f'PUT {primary_reg}')


                    else:
                        address = self.memory.get_array_at_index(memory_cell[1], 0)
                        secondary_address = self.memory.get_variable(index[1])
                        self.gen_number(secondary_address, secondary_reg)
                        self.code.append(f'LOAD {secondary_reg}')
                        self.gen_number(address, primary_reg)
                        self.code.append(f'ADD {primary_reg}')
                        self.code.append(f'PUT {primary_reg}')

    def initialize(self, target):
        if target[0] != 'variable':
            return
        name = target[1]

        if name in self.memory:
                    if isinstance(self.memory[name], Variable):
                        self.memory[name].initialized = True

    def notInitialized(self, target):
        if target[0] != 'variable':
            return False
        name = target[1]

        if name in self.memory:
                    if isinstance(self.memory[name], Variable):
                        return not self.memory[name].initialized
