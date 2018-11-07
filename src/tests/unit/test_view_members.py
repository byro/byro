from decimal import Decimal

from byro.office.views.members import filter_excel_de


def test_windows_de_comma():
    assert filter_excel_de(0.01) == "0,01"
    assert filter_excel_de(0.1) == "0,10"
    assert filter_excel_de(1.0) == "1,00"
    assert filter_excel_de(1234.56) == "1.234,56"
    assert filter_excel_de(1234567890.123) == "1.234.567.890,12"

    assert filter_excel_de(Decimal("0.01")) == "0,01"
    assert filter_excel_de(Decimal("0.1")) == "0,10"
    assert filter_excel_de(Decimal("1.0")) == "1,00"
    assert filter_excel_de(Decimal("1234.56")) == "1.234,56"
    assert filter_excel_de(Decimal("1234567890.123")) == "1.234.567.890,12"
