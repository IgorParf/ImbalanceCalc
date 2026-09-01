# ImbalanceCalc

Застосунок для розрахунку платежу за небаланси електричної енергії.

Користувач завантажує файл з даними через веб-інтерфейс, дані перераховуються
відповідно до методики, після чого формується:

- **загальний платіж** за небаланси за весь період;
- **аналіз по добах** — обсяги та платіж за кожну добу;
- **окремий блок** із добами, платіж за які перевищує **10 000 грн**;
- **Excel-звіт** для вивантаження.

## Встановлення

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e ".[dev]"
```

## Запуск

Веб-інтерфейс:

```bash
streamlit run app.py
```

Консольний варіант:

```bash
imbalance-calc data/input/файл.xlsx -o data/output/report.xlsx
```

Тести:

```bash
pytest
```

## Структура

```
app.py                       точка входу Streamlit
src/imbalance_calc/
    config.py                константи та налаштування (поріг 10 000 грн тощо)
    models.py                PeriodRecord, DayResult, SettlementResult
    exceptions.py            винятки пакета
    cli.py                   консольний інтерфейс
    dataio/                  читання та валідація файлів
        schema.py            очікувані колонки та їх синоніми
        loaders.py           xlsx/csv -> нормалізовані записи
        validators.py        перевірка повноти й коректності даних
    core/                    розрахункове ядро
        methodology.py       перерахунок за методикою
        imbalance.py         обсяг небалансу та платіж за період
        settlement.py        загальний платіж
        daily.py             добові підсумки та відбір діб понад поріг
    reporting/               звіти
        summary.py           таблиці та текстовий підсумок
        excel_report.py      вивантаження в xlsx
    ui/                      інтерфейс
        app.py               головна сторінка
        components.py        елементи інтерфейсу
tests/                       тести (поки заглушки)
data/input | output | samples
docs/methodology.md          опис методики
```

## Стан

Каркас проєкту. Розрахункова логіка позначена `NotImplementedError`;
формули методики уточнюються в [docs/methodology.md](docs/methodology.md).
