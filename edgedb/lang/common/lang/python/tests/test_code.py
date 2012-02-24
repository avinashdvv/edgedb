##
# Copyright (c) 2012 Sprymix Inc.
# All rights reserved.
#
# See LICENSE for details.
##


import dis
import types

from semantix.utils.debug import assert_raises

from ..code import Code, opcodes, _SUPPORTED_FLAGS


class TestLangPythonCode:
    def disassemble(self, co):
        code = co.co_code
        linestarts = dict(dis.findlinestarts(co))
        labels = dis.findlabels(code)
        n = len(code)
        i = 0
        extended_arg = 0
        free = None
        result = []
        while i < n:
            op = code[i]
            if i in linestarts:
                result.append(linestarts[i])
            else:
                result.append('#')

            if i in labels:
                result.append('>>')
            else:
                result.append('--')

            result.append(i)
            result.append(dis.opname[op])
            i += 1
            if op >= dis.HAVE_ARGUMENT:
                oparg = code[i] + code[i + 1] * 256 + extended_arg
                i += 2

                extended_arg = 0
                if op == dis.EXTENDED_ARG:
                    extended_arg = oparg * 65536

                if op in dis.hasconst:
                    result.append(('const', co.co_consts[oparg]))
                elif op in dis.hasname:
                    result.append(('name', co.co_names[oparg]))
                elif op in dis.hasjrel:
                    result.append(('jrel', oparg + i))
                elif op in dis.haslocal:
                    result.append(('local', co.co_varnames[oparg]))
                elif op in dis.hascompare:
                    result.append(('cmp', oparg))
                elif op in dis.hasfree:
                    if free is None:
                        free = co.co_cellvars + co.co_freevars
                    result.append(('free', free[oparg]))
                else:
                    result.append(('arg', oparg))
        return tuple(result)

    def compare_codes(self, code1, code2):
        fields = 'co_argcount', 'co_kwonlyargcount', 'co_nlocals', \
                 'co_varnames', 'co_filename', 'co_name', 'co_firstlineno', \
                 'co_freevars', 'co_cellvars'

        for field in fields:
            attr1 = getattr(code1, field)
            attr2 = getattr(code2, field)

            if isinstance(attr1, tuple):
                attr1 = set(attr1)

            if isinstance(attr2, tuple):
                attr2 = set(attr2)

            assert attr1 == attr2, field

        dis_code1 = self.disassemble(code1)
        dis_code2 = self.disassemble(code2)
        assert dis_code1 == dis_code2

        lines1 = dict(dis.findlinestarts(code1))
        lines2 = dict(dis.findlinestarts(code2))
        assert lines1 == lines2

        code1_flags = code1.co_flags & _SUPPORTED_FLAGS
        code2_flags = code2.co_flags & _SUPPORTED_FLAGS
        assert code1_flags == code2_flags

    def check_on(self, code_obj):
        new_code_obj = Code.from_code(code_obj).to_code()
        self.compare_codes(code_obj, new_code_obj)


    def test_utils_lang_python_code_object(self):
        '''Basic test of the Code object.  Tests that all internal
        structures (varnames, cellvars, freenames etc) are initialized
        correctly.  At the end we try to disassemble code of 'test' function,
        assemble it back and try to execute it again.'''

        free = []
        def test(a, b, c=10, *args, kw=5, kwonly=10, **kwargs):
            local = min(a, b) * c + kw + kwonly + 42
            if a > b:
                local += a
            free.append(local)
            func = lambda: local
            yield func()

        orig_code = test.__code__
        code = Code.from_code(orig_code)

        assert code.vararg == 'args'
        assert code.varkwarg == 'kwargs'

        assert code.newlocals
        assert code.filename.endswith('.py')
        assert code.firstlineno > 5
        assert code.name == 'test'

        assert code.args == {'a', 'b', 'c'}
        assert code.kwonlyargs == {'kw', 'kwonly'}

        assert opcodes.YIELD_VALUE in {op.__class__ for op in code.ops}
        new_code = code.to_code()
        self.compare_codes(new_code, orig_code)

        old_val1 = list(test(2, 1))
        old_val2 = list(test(1, 2, kw_only=100))
        test.__code__ = new_code
        assert list(test(2, 1)) == old_val1
        assert list(test(1, 2, kw_only=100)) == old_val2
        assert free[0] == free[2]
        assert free[1] == free[3]

    def test_utils_lang_python_code_funcargs(self):
        '''Check how well we handle different arguments schemas'''

        def test0(): pass
        self.check_on(test0.__code__)

        def test1(a, b): pass
        self.check_on(test1.__code__)

        def test2(*, a): pass
        self.check_on(test2.__code__)

        def test3(a, *, b): pass
        self.check_on(test3.__code__)

        def test4(a, b=1): pass
        self.check_on(test4.__code__)

        def test5(a, *, b=1): pass
        self.check_on(test5.__code__)

        def test6(*args): pass
        self.check_on(test6.__code__)

        def test7(**args): pass
        self.check_on(test7.__code__)

        def test8(*ar, **args): pass
        self.check_on(test8.__code__)

        def test9(a, b, c=10, *ar, foo, **args): pass
        self.check_on(test9.__code__)

        def test10(*, foo, **args): pass
        self.check_on(test10.__code__)

    def test_utils_lang_python_code_mod(self):
        '''Test how we can modify the __code__ object.
        In this test we turn a regular python function into a generator'''

        def test(a):
            return a ** 2

        assert test(10) == 100
        with assert_raises(TypeError):
            list(test(10))

        code = Code.from_code(test.__code__)

        assert code.ops[-1].__class__ is opcodes.RETURN_VALUE
        del code.ops[-1]
        code.ops.extend((opcodes.YIELD_VALUE(),
                         opcodes.POP_TOP(),
                         opcodes.LOAD_CONST(const=None),
                         opcodes.RETURN_VALUE()))
        test.__code__ = code.to_code()

        assert list(test(10)) == [100]

    def test_utils_lang_python_code_decimal_assemble_disassemble(self):
        '''Disassembles and then assembles back code objects of decimal
        module's functions and methods, and compares the new code objects
        to the old ones'''

        import decimal

        mod = decimal

        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)

            if isinstance(attr, types.FunctionType):
                #print('>>>>', attr_name)
                self.check_on(attr.__code__)

            elif isinstance(attr, type):
                cls = attr
                for attr_name in dir(cls):
                    attr = getattr(cls, attr_name)

                    if isinstance(attr, types.FunctionType):
                        #print('>>>>', cls.__name__, '::', attr_name)
                        self.check_on(attr.__code__)