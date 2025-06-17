from .static import VOLUME_IDENTIFIER
from wine_spider.exceptions import NoPreDefinedVolumeIdentifierException

def unit_format_to_volume(unit_format):    
    volume = VOLUME_IDENTIFIER.get(unit_format, None)
    if not volume:
        raise NoPreDefinedVolumeIdentifierException(unit_format)

    return volume