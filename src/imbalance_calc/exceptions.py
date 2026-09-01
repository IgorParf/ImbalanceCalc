"""Винятки пакета."""


class ImbalanceCalcError(Exception):
    """Базовий виняток."""


class FileFormatError(ImbalanceCalcError):
    """Непідтримуваний формат або пошкоджений файл."""


class ValidationError(ImbalanceCalcError):
    """Вхідні дані не відповідають очікуваній структурі."""


class MethodologyError(ImbalanceCalcError):
    """Помилка в застосуванні методики розрахунку."""
