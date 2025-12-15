from autopilot.tools.calculator import CalculatorCLI


def test_calculator_tool():
  tool = CalculatorCLI()
  assert tool.compute("1 + 1") == 2
