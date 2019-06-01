import ast
import logging
import math
import operator as op

import pajbot.exc
import pajbot.models
from pajbot.actions import ActionQueue
from pajbot.models.command import Command
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.utils import time_limit

log = logging.getLogger(__name__)


class PBMath:
    """
    Source: http://stackoverflow.com/a/9558001
    """

    # supported operators
    operators = {
        ast.Add: op.add,
        ast.Sub: op.sub,
        ast.Mult: op.mul,
        ast.Div: op.truediv,
        ast.Pow: op.pow,
        ast.BitXor: op.xor,
        ast.USub: op.neg,
        ast.RShift: op.rshift,
        ast.LShift: op.lshift,
    }

    @staticmethod
    def eval_expr(expr):
        """
        >>> eval_expr('2^6')
        4
        >>> eval_expr('2**6')
        64
        >>> eval_expr('1 + 2*3**(4^5) / (6 + -7)')
        -5.0
        """
        return PBMath.eval_(ast.parse(expr, mode="eval").body)

    @staticmethod
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

    ID = __name__.split(".")[-1]
    NAME = "Math"
    DESCRIPTION = "Adds a !math command for simple arithmetic"
    CATEGORY = "Feature"

    SETTINGS = [
        ModuleSetting(
            key="online_global_cd",
            label="Global cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=2,
            constraints={"min_value": 0, "max_value": 120},
        ),
        ModuleSetting(
            key="online_user_cd",
            label="Per-user cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=6,
            constraints={"min_value": 0, "max_value": 240},
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)
        self.action_queue = ActionQueue()
        self.action_queue.start()

    def load_commands(self, **options):
        self.commands["math"] = Command.raw_command(
            self.math,
            delay_all=self.settings["online_global_cd"],
            delay_user=self.settings["online_user_cd"],
            description="Calculate some simple math",
            examples=[],
        )

    @staticmethod
    def do_math(bot, source, message):
        expr_res = None
        with time_limit(1):
            try:
                expr_res = PBMath.eval_expr("".join(message))
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
            except pajbot.exc.TimeoutException:
                # took longer than 1 second
                pass
            except:
                log.exception("Uncaught exception in Math module")

        if expr_res is None:
            return False

        emote = "Kappa"
        try:
            if int(expr_res) == 69 or expr_res == 69.69:
                emote = "Kreygasm"
            elif int(expr_res) == 420:
                emote = "CiGrip"
        except:
            pass

        bot.say("{}, {} {}".format(source.username_raw, expr_res, emote))

    def math(self, **options):
        bot = options["bot"]
        source = options["source"]
        message = options["message"]

        if source.username == "karl_kons":
            bot.say("{}, 8 Kappa".format(source.username_raw))
            return True

        if message:
            message = message.replace("pi", str(math.pi))
            message = message.replace("e", str(math.e))
            message = message.replace("π", str(math.pi))
            message = message.replace("^", "**")
            message = message.replace(",", ".")

            self.do_math(bot, source, message)
