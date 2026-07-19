from dataclasses import FrozenInstanceError
import pytest
from config import Config
from Compass.instrument import Instrument
from models.compass import (KeySignature, TonalMode)


def test_config_is_immutable():
    config = Config()

    with pytest.raises(FrozenInstanceError):
        config.sensivity = 0.8

def test_default_instrument_is_piano():
    config = Config()

    assert config.instrument == Instrument.piano()

def test_accepts_manual_key_and_bpm():
    key = KeySignature(
        accidents_qunatity=2,
        tonic="D",
        mode=TonalMode.MAJOR
    )
    config = Config(
        manual_key=key,
        manual_bpm=120
    )

    assert config.manual_key == key
    assert config.manual_bpm == 120