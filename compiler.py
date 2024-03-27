import sys
from sly import Lexer, Parser
from generator import Generator

class MyLexer(Lexer):
    tokens = {PROGRAM, PROCEDURE, IS, IN, END, IF, THEN, ELSE, ENDIF, WHILE, DO, ENDWHILE, REPEAT, UNTIL, READ, WRITE, PID, GETS, NUM, EQ, NEQ, GEQ, LEQ, GT, LT}
    ignore = " \t"
    literals = {'+', '-', '*', '/', '%', '(', ')', '[', ']', ';', ',', "T"}

    @_(r'\#.*')
    def COMMENT(self, t):
        pass

    PROGRAM = r'PROGRAM'
    PROCEDURE = r'PROCEDURE'

    ENDWHILE = r'ENDWHILE'
    ENDIF = r'ENDIF'
    END = r'END'

    IS = r'IS'
    IN = r'IN'

    IF = r'IF'
    THEN = r'THEN'
    ELSE = r'ELSE'

    WHILE = r'WHILE'
    DO = r'DO'

    REPEAT = r'REPEAT'
    UNTIL = r'UNTIL'

    READ = r'READ'
    WRITE = r'WRITE'

    GETS = r':='
    EQ = r'='
    NEQ =r'!='
    GEQ = r'>='
    LEQ = r'<='
    GT = r'>'
    LT = r'<'

    PID = r'[_a-z]+'
    @_(r'\d+')
    def NUM(self, t):
        t.value = int(t.value)
        return t

    # Ignored pattern
    ignore_newline = r'\n+'

    # Extra action for newlines
    def ignore_newline(self, t):
        self.lineno += t.value.count('\n')

    def error(self, t):
        print(f'Line {self.lineno}: illegal character {t.value[0]}')
        self.index += 1

class MyParser(Parser):
    tokens = MyLexer.tokens
    generator = Generator()
    
    @_('procedures main')
    def program_all(self, p):
        for procedure in p.procedures:
            self.generator.gen_procedure(*procedure)
        self.generator.gen(*p.main)

    @_('procedures PROCEDURE proc_head IS declarations IN commands END')
    def procedures(self, p):
        return p.procedures + [(p.proc_head, p.declarations, p.commands)]

    @_('procedures PROCEDURE proc_head IS IN commands END')
    def procedures(self, p):
        return p.procedures + [(p.proc_head, [], p.commands)]

    @_('')
    def procedures(self, p):
        return []

    @_('PROGRAM IS declarations IN commands END')
    def main(self, p):
        return p.declarations, p.commands

    @_('PROGRAM IS IN commands END')
    def main(self, p):
        return [], p.commands

    @_('commands command')
    def commands(self, p):
        return p.commands + [p.command]

    @_('command')
    def commands(self, p):
        return [p.command]

    # commands

    @_('identifier GETS expression ";"')
    def command(self, p):
        return 'assign', p.identifier, p.expression, p.lineno

    @_('IF condition THEN commands ELSE commands ENDIF')
    def command(self, p):
        return 'ifelse', p.condition, p.commands0, p.commands1

    @_('IF condition THEN commands ENDIF')
    def command(self, p):
        return 'ifelse', p.condition, p.commands, []

    @_('WHILE condition DO commands ENDWHILE')
    def command(self, p):
        return 'while', p.condition, p.commands

    @_('REPEAT commands UNTIL condition ";"')
    def command(self, p):
        return 'repeat', p.condition, p.commands

    @_('proc_call ";"')
    def command(self, p):
        return 'call', p.proc_call

    @_('READ identifier ";"')
    def command(self, p):
        return 'read', p.identifier, p.lineno

    @_('WRITE value ";"')
    def command(self, p):
        return 'write', p.value, p.lineno

    @_('PID "(" args_decl ")"')
    def proc_head(self, p):
        return p.PID, p.args_decl, p.lineno

    @_('PID "(" args ")"')
    def proc_call(self, p):
        return p.PID, p.args, p.lineno

    @_('declarations "," PID')
    def declarations(self, p):
        return p.declarations + [("variable", p.PID, p.lineno)]

    @_('declarations "," PID "[" NUM "]"')
    def declarations(self, p):
        return p.declarations + [("array", p.PID, p.NUM, p.lineno)]

    @_('PID')
    def declarations(self, p):
        return [("variable", p.PID, p.lineno)]

    @_('PID "[" NUM "]"')
    def declarations(self, p):
        return [("array", p.PID, p.NUM, p.lineno)]
    
    @_('args_decl "," PID')
    def args_decl(self, p):
        return p.args_decl + [('variable', p.PID)]

    @_('args_decl "," "T" PID')
    def args_decl(self, p):
        return p.args_decl + [('array', p.PID)]

    @_('PID')
    def args_decl(self, p):
        return [('variable', p.PID)]

    @_('"T" PID')
    def args_decl(self, p):
        return [('array', p.PID)]

    @_('args "," PID')
    def args(self, p):
        return p.args + [p.PID]

    @_('PID')
    def args(self, p):
        return [p.PID]

    # expressions

    @_('value')
    def expression(self, p):
        return p.value

    @_('value "+" value')
    def expression(self, p):
        return "add", p.value0, p.value1

    @_('value "-" value')
    def expression(self, p):
        return "sub", p.value0, p.value1
    
    @_('value "*" value')
    def expression(self, p):
        return "mul", p.value0, p.value1

    @_('value "/" value')
    def expression(self, p):
        return "div", p.value0, p.value1

    @_('value "%" value')
    def expression(self, p):
        return "mod", p.value0, p.value1

    # conditions

    @_('value EQ value')
    def condition(self, p):
        return "eq", p.value0, p.value1

    @_('value NEQ value')
    def condition(self, p):
        return "neq", p.value0, p.value1

    @_('value GT value')
    def condition(self, p):
        return "gt", p.value0, p.value1

    @_('value LT value')
    def condition(self, p):
        return "lt", p.value0, p.value1

    @_('value GEQ value')
    def condition(self, p):
        return "geq", p.value0, p.value1

    @_('value LEQ value')
    def condition(self, p):
        return "leq", p.value0, p.value1

    @_('NUM')
    def value(self, p):
        return "number", p.NUM

    @_("identifier")
    def value(self, p):
        return "load", p.identifier

    @_('PID')
    def identifier(self, p):
        return "variable", p.PID

    @_('PID "[" NUM "]"')
    def identifier(self, p):
        return "array", p.PID, ("number", p.NUM)

    @_('PID "[" PID "]"')
    def identifier(self, p):
        return "array", p.PID0, ("load", p.PID1)
    
    # def error(self, p):
    #     print(f'Line {p.lineno}: unexpected token {p.type}')
    #     self.errok()

    # @_('READ error ";"')
    # def command(self, p):
    #     print(f'Line {p.lineno}: incorrect READ statement')
    #     return "error"

if __name__ == '__main__':
    lexer = MyLexer()
    parser = MyParser()
    with open(sys.argv[1]) as in_f:
        text = in_f.read()

    parser.parse(lexer.tokenize(text))
    generator = parser.generator

    if not generator.errorMode:
        with open(sys.argv[2], 'w') as out_f:
            for line in generator.code:
                print(line, file=out_f)