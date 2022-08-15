import binascii
import brownie
import pytest

from brownie import TestSet

# enforce function isolation for tests below
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

def test_empty_set(owner):
    intSet = _deploySet(owner);

    assert intSet.size() == 0
    assert intSet.contains(42) == False


def test_add_elements(owner):
    intSet = _deploySet(owner);

    intSet.add(2)
    intSet.add(3)
    intSet.add(5)
    intSet.add(42)

    assert intSet.size() == 4
    assert intSet.contains(1) == False
    assert intSet.contains(2) == True
    assert intSet.contains(3) == True
    assert intSet.contains(4) == False
    assert intSet.contains(5) == True
    assert intSet.contains(42) == True


def test_remove_1st_element(owner):
    intSet = _deploySet(owner);

    intSet.add(1)
    intSet.add(2)
    intSet.add(3)
    intSet.add(4)
    intSet.add(5)

    assert intSet.size() == 5
    assert intSet.contains(1) == True
    assert intSet.contains(2) == True
    assert intSet.contains(3) == True
    assert intSet.contains(4) == True
    assert intSet.contains(5) == True

    intSet.remove(1)

    assert intSet.size() == 4
    assert intSet.contains(1) == False
    assert intSet.contains(2) == True
    assert intSet.contains(3) == True
    assert intSet.contains(4) == True
    assert intSet.contains(5) == True


def test_remove_middle_element(owner):
    intSet = _deploySet(owner);

    intSet.add(1)
    intSet.add(2)
    intSet.add(3)
    intSet.add(4)
    intSet.add(5)

    assert intSet.size() == 5
    assert intSet.contains(1) == True
    assert intSet.contains(2) == True
    assert intSet.contains(3) == True
    assert intSet.contains(4) == True
    assert intSet.contains(5) == True

    intSet.remove(3)

    assert intSet.size() == 4
    assert intSet.contains(1) == True
    assert intSet.contains(2) == True
    assert intSet.contains(3) == False
    assert intSet.contains(4) == True
    assert intSet.contains(5) == True


def test_remove_last_element(owner):
    intSet = _deploySet(owner);

    intSet.add(1)
    intSet.add(2)
    intSet.add(3)
    intSet.add(4)
    intSet.add(5)

    assert intSet.size() == 5
    assert intSet.contains(1) == True
    assert intSet.contains(2) == True
    assert intSet.contains(3) == True
    assert intSet.contains(4) == True
    assert intSet.contains(5) == True

    intSet.remove(5)

    assert intSet.size() == 4
    assert intSet.contains(1) == True
    assert intSet.contains(2) == True
    assert intSet.contains(3) == True
    assert intSet.contains(4) == True
    assert intSet.contains(5) == False


def test_add_remove_elements(owner):
    intSet = _deploySet(owner);

    intSet.add(1)
    intSet.add(2)
    intSet.add(3)

    assert intSet.size() == 3
    assert intSet.contains(1) == True
    assert intSet.contains(2) == True
    assert intSet.contains(3) == True

    # adding element already in set should not change anything
    intSet.add(1)
    assert intSet.size() == 3
    assert intSet.contains(1) == True
    assert intSet.contains(2) == True
    assert intSet.contains(3) == True

    # remove 1st elemnt
    intSet.remove(1)
    assert intSet.size() == 2
    assert intSet.contains(1) == False
    assert intSet.contains(2) == True
    assert intSet.contains(3) == True

    # removing an element not in the set should not change anything
    intSet.remove(1)
    assert intSet.size() == 2
    assert intSet.contains(1) == False
    assert intSet.contains(2) == True
    assert intSet.contains(3) == True

    # readding the removed element should product the initial situation
    intSet.add(1) 
    assert intSet.size() == 3
    assert intSet.contains(1) == True
    assert intSet.contains(2) == True
    assert intSet.contains(3) == True


def test_int_at(owner):
    intSet = _deploySet(owner);

    for i in range(5):
        intSet.add(i)

    for i in range(intSet.size()):
        assert intSet.contains(i)
        assert i == intSet.intAt(i)

    with brownie.reverts("ERROR:SET-001:INDEX_TOO_LARGE"):
        assert 42 == intSet.intAt(5)


def _deploySet(owner) -> TestSet:
    return  TestSet.deploy({'from': owner})