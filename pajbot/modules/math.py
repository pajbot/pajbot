import logging
import math
import ast
import operator as op

from pajbot.modules import BaseModule
from pajbot.models.command import Command, CommandExample
from pajbot.actions import ActionQueue
from pajbot.tbutil import time_limit, TimeoutException

log = logging.getLogger('pajbot')


class PBMath:
    """
    Source: http://stackoverflow.com/a/9558001
    """
    # supported operators
    operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
                 ast.Div: op.truediv, ast.Pow: op.pow, ast.BitXor: op.xor,
                 ast.USub: op.neg, ast.RShift: op.rshift, ast.LShift: op.lshift}

    def eval_expr(expr):
        """
        >>> eval_expr('2^6')
        4
        >>> eval_expr('2**6')
        64
        >>> eval_expr('1 + 2*3**(4^5) / (6 + -7)')
        -5.0
        """
        return PBMath.eval_(ast.parse(expr, mode='eval').body)

    def eval_(node):
        if isinstance(node, ast.Num):  # <number>
            return node.n
        elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
            return PBMath.operators[type(node.op)](PBMath.eval_(node.left), PBMath.eval_(node.right))
        elif isinstance(node, ast.UnaryOp):  # <operator> <operand> e.g., -1
            return PBMath.operators[type(node.op)](PBMath.eval_(node.operand))
        else:
            raise TypeError(node)

class MathModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Math'
    DESCRIPTION = 'Adds a !math command for simple arithmetic'

    def __init__(self):
        super().__init__()
        self.action_queue = ActionQueue()
        self.action_queue.start()

    def load_commands(self, **options):
        # TODO: Have delay modifiable in settings

        self.commands['math'] = Command.raw_command(self.math,
                delay_all=2,
                delay_user=6,
                description='Calculate some simple math',
                examples=[
                    ],
                )

    def do_math(self, bot, source, message):
        expr_res = None
        with time_limit(1):
            try:
                expr_res = PBMath.eval_expr(''.join(message))
            except OverflowError:
                # Result is too big
                pass
            except KeyError:
                # Something wrong with the operator
                pass
            except TypeError:
                # Something wrong with the evaluation
                pass
            except SyntaxError:
                # Something invalid was passed through message
                pass
            except TimeoutException:
                # took longer than 1 second
                pass
            except:
                log.exception('Uncaught exception in Math module')

        if expr_res is None:
            return False

        emote = 'Kappa'
        if int(expr_res) == 69 or expr_res == 69.69:
            emote = 'Kreygasm'
        elif int(expr_res) == 420:
            emote = 'CiGrip'

        bot.say('{}, {} {}'.format(source.username_raw, expr_res, emote))

    def math(self, **options):
        bot = options['bot']
        source = options['source']
        message = options['message']

        if message:
            message = message.replace('pi', str(math.pi))
            message = message.replace('e', str(math.e))
            message = message.replace('π', str(math.pi))
            message = message.replace('^', '**')
            message = message.replace(',', '.')

            self.do_math(bot, source, message)
