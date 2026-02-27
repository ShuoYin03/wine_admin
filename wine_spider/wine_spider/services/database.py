from shared.database.lots_client import LotsClient
from shared.database.auctions_client import AuctionsClient
from shared.database.lot_items_client import LotItemsClient
from shared.database.auction_sales_client import AuctionSalesClient
from shared.database.fx_rates_client import FxRatesClient
from shared.database.lwin_matching_client import LwinMatchingClient

lots_client = LotsClient()
auctions_client = AuctionsClient()
lot_items_client = LotItemsClient()
auction_sales_client = AuctionSalesClient()
fx_rates_client = FxRatesClient()
lwin_matching_client = LwinMatchingClient()