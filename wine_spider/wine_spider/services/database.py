from database import (
    LotsClient,
    AuctionsClient,
    LotItemsClient,
    AuctionSalesClient,
    FxRatesClient,
    LwinMatchingClient,
)

lots_client = LotsClient()
auctions_client = AuctionsClient()
lot_items_client = LotItemsClient()
auction_sales_client = AuctionSalesClient()
fx_rates_client = FxRatesClient()
lwin_matching_client = LwinMatchingClient()