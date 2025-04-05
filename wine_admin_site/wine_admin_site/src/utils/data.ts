export const keyMap: Record<string, string> = {
    "Auction House": "auction_house",
    "Lot Producer": "lot_producer",
    "Region": "region",
    "Colour": "color",
    "Format": "format",
    "Vintage": "vintage",
    "Auction Before": "start_date",
    "Auction After": "end_date",
    "Price Range": "end_price",
};

export const AuctionHouseOptions = [
    "Sotheby's",
]

export const LotProducerOptions = [
    "Château Lafite Rothschild",
    "Château Margaux",
]

export const RegionOptions = [
    "Bordeaux",
    "Burgundy",
]

export const ColourOptions = [
    "Red",
    "White",
]

export const FormatOptions = [
    "750ml",
    "375ml",
]

export const keyMapOptions: Record<string, Array<string>> = {
    "auction_house": AuctionHouseOptions,
    "lot_producer": LotProducerOptions,
    "region": RegionOptions,
    "color": ColourOptions,
    "format": FormatOptions,
    "vintage": ["vintage", "vintage"],
    "country": ["country", "country"],
  };