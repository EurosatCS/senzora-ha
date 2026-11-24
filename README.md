# Eurosat Meters pro Home Assistant

[![Validate](https://github.com/EurosatCS/eurosat-meters-ha/actions/workflows/validate.yml/badge.svg)](https://github.com/EurosatCS/eurosat-meters-ha/actions/workflows/validate.yml)
[![Tests](https://github.com/EurosatCS/eurosat-meters-ha/actions/workflows/tests.yml/badge.svg)](https://github.com/EurosatCS/eurosat-meters-ha/actions/workflows/tests.yml)
[![Release](https://img.shields.io/github/v/release/EurosatCS/eurosat-meters-ha)](https://github.com/EurosatCS/eurosat-meters-ha/releases)

Integrace načítá z vašeho účtu Eurosat stavy elektroměrů, vodoměrů a dalších měřičů
a zobrazuje je v Home Assistantu jako senzory. Stačí zadat API klíč, nic se nepíše do YAML.

*English summary below.*

- Pro každý měřič dostupný pod vaším klíčem vznikne senzor. Nové měřiče se přidají samy.
- Elektroměry (kWh) a vodoměry (m³) jdou rovnou přidat do panelu **Energie**.
- Data se stahují jednou za hodinu, interval lze změnit na 5 až 1440 minut.
- Když API klíč přestane platit, Home Assistant si sám řekne o nový.

**Potřebujete:** Home Assistant 2024.12 nebo novější a API klíč k účtu Eurosat ve tvaru `1234567;abcdef…`.

## Instalace

### Přes Marketplace (doporučeno)

Od verze 2026.11 je HACS součástí Home Assistantu pod názvem Marketplace.

1. Otevřete **Nastavení → Marketplace**.
2. Přidejte vlastní repozitář odkazem `https://github.com/EurosatCS/eurosat-meters-ha`, typ **Integrace**.
3. Při prvním přidání vlastního repozitáře se přihlaste účtem GitHub a potvrďte upozornění *I understand the risks*.
4. Nainstalujte **Eurosat Meters** a restartujte Home Assistant.

Home Assistant vám pak sám nabídne nové verze. Ve verzích 2026.10 a starších je postup
stejný v HACS (nabídka vpravo nahoře → **Vlastní repozitáře**).

### Ručně

1. Z [posledního vydání](https://github.com/EurosatCS/eurosat-meters-ha/releases/latest) stáhněte *Source code (zip)* a rozbalte ho.
2. Složku `custom_components/eurosat_meters` zkopírujte do `/config/custom_components/`. Pokud složka `custom_components` neexistuje, vytvořte ji.
3. Restartujte Home Assistant.

K souborům v `/config` se dostanete například doplňkem File editor, Studio Code Server nebo přes sdílení Samba.

Po restartu se v logu objeví varování, že vlastní integrace nebyla testována týmem
Home Assistantu. Zobrazuje se u každé vlastní integrace a nic neznamená.

## Nastavení

1. **Nastavení → Zařízení a služby → Přidat integraci** a vyhledejte **Eurosat Meters**.
2. Vložte API klíč celý, včetně čísla před středníkem.
3. Pole *ID skupiny* nechte prázdné. Vyplňuje se jen tehdy, když chcete číst jinou než domovskou skupinu.
4. Potvrďte. Klíč se ihned ověří a senzory se vytvoří.

Interval aktualizace změníte v integraci tlačítkem **Nastavit** (výchozí 60 minut).
U vodoměrů kratší interval nepomůže, protože nový odečet posílají až po několika hodinách.

> [!WARNING]
> API klíč je přístupový údaj k vašemu účtu. Nevkládejte ho do issues, logů ani snímků obrazovky.

## Co v Home Assistantu uvidíte

Každá komunikační jednotka se zobrazí jako zařízení `Eurosat <IMEI>` a každý její měřič jako senzor.

| Jednotka z API | Senzor v Home Assistantu |
|---|---|
| `KWh`, `Wh`, `MWh` | energie, celkový narůstající stav |
| `m3`, `l` | voda, celkový narůstající stav |
| `°C`, `V`, `kg`, `%` | okamžitá hodnota |
| jiná | okamžitá hodnota s původní jednotkou |

- **Pojmenování:** měřič s popiskem v portálu Eurosat převezme popisek jako název entity, jinak se jmenuje `Meter <ID>`.
  Od Home Assistantu 2026.11 se zobrazený název skládá z názvu zařízení a entity, takže stačí přejmenovat zařízení (např. na „Voda byt“).
- **Čas odečtu:** atribut `measured_at` ukazuje, kdy měřič hodnotu skutečně odečetl. Měřiče nehlásí ve stejnou chvíli.
- **Stáří dat:** API vrací jen odečty staré nejvýše 31 dní; měřič, který déle nic neposlal, je nedostupný.

## Panel Energie

1. Otevřete **Nastavení → Panely → Energie**.
2. Vodoměr přidejte v části **Spotřeba vody**.
3. Elektroměr přidejte v části pro elektřinu: hlavní jako odběr ze sítě, podružné jako jednotlivá zařízení.

První sloupce se v grafu objeví po jedné až dvou hodinách. Měřiče v m³ se řadí jako voda;
plynoměr by se proto zobrazil mezi vodoměry. Pokud ho máte, [založte issue](https://github.com/EurosatCS/eurosat-meters-ha/issues).

### Tip: podružný vodoměr

Vlastní spotřebu za hlavním a podružným vodoměrem spočítáte jako rozdíl obou stavů.
Do `configuration.yaml` přidejte (a `sensor.HLAVNI` / `sensor.PODRUZNY` nahraďte ID entit):

```yaml
template:
  - sensor:
      - name: Voda vlastní spotřeba
        unique_id: voda_vlastni_spotreba
        unit_of_measurement: m³
        device_class: water
        state_class: total
        state: >
          {{ (states("sensor.HLAVNI") | float - states("sensor.PODRUZNY") | float) | round(3) }}
        availability: >
          {{ has_value("sensor.HLAVNI") and has_value("sensor.PODRUZNY") }}
```

Ponechte `state_class: total`, ne `total_increasing`: oba vodoměry odečítají v jiný čas,
rozdíl může krátce klesnout a `total_increasing` by to vyhodnotil jako výměnu měřiče.

## Řešení potíží

| Co se děje | Příčina a řešení |
|---|---|
| Integrace nejde vyhledat | Složka není v `/config/custom_components/eurosat_meters`, nebo neproběhl restart. Vymažte i mezipaměť prohlížeče. |
| „API klíč byl odmítnut“ | Klíč je neúplný nebo neplatný. Vložte ho celý, včetně čísla a středníku. |
| Integrace po čase žádá nový klíč | Klíč přestal platit. Zadejte nový; senzory i historie zůstanou. |
| „Příliš mnoho požadavků“ | API omezuje počet dotazů. Počkejte pár minut a nenastavujte zbytečně krátký interval. |
| Senzor je nedostupný | Měřič přes 31 dní nic neposlal; ověřte ho v portálu Eurosat. |
| Hodnota se dlouho nemění | Podívejte se na atribut `measured_at`; zobrazuje se poslední odečet, který měřič poslal. |
| V logu je „Could not load meter labels“ | Nepodařilo se načíst popisky. Na hodnoty to nemá vliv; senzory pojmenujte ručně. |
| Chybí měřič, který v portálu vidíte | Klíč čte domovskou skupinu. Měřič z jiné skupiny přidejte jako další záznam integrace s vyplněným ID skupiny. |

Chybu nahlaste přes [Issues](https://github.com/EurosatCS/eurosat-meters-ha/issues).

## English

Custom integration that reads electricity, water and other meter readings from the
Eurosat REST API (`cars.eurosat.cz`) and exposes them as Home Assistant sensors.
Install it from **Settings → Marketplace** (HACS on 2026.10 and older) by adding this
repository as a custom repository of type *Integration*, then add **Eurosat Meters**
under **Settings → Devices & services** and enter your API key. Energy (kWh) and water (m³)
sensors work directly in the Energy dashboard.

## Vývoj

```bash
pip install -r requirements_test.txt
pytest
```

Nové vydání: zvyšte `version` v `custom_components/eurosat_meters/manifest.json`,
doplňte `CHANGELOG.md` a na GitHubu vytvořte release s tagem `v<verze>` (např. `v0.1.2`).

## Licence

[MIT](LICENSE)
