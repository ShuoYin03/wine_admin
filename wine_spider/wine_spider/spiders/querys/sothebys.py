LOT_ID_QUERY = """
    query LotQuery($id: String!, $countryOfOrigin: String, $language: TranslationLanguage!, $auctionId: String!) {
        lot: lotV2(lotId: $id, countryOfOrigin: $countryOfOrigin, language: $language) {
            ... on LotV2 {
                __typename
                auction {
                    __typename
                    auctionId
                    lotCards(filter: ALL, countryOfOrigin: $countryOfOrigin) {
                        ...LotNavigationDropdownLotFragment
                    }
                }
            }
        }
        auctionAutochargeConfig(auctionId: $auctionId) {
            __typename
        }
    }
    
    fragment LotNavigationDropdownLotFragment on LotCard {
        lotId
        slug {
            lotSlug
            auctionSlug {
                year
                name
            }
        }
    }
"""

LOT_DESCRIPTION_QUERY = """
    query LotQuery($id: String!, $countryOfOrigin: String, $language: TranslationLanguage!) {
        lot: lotV2(lotId: $id, countryOfOrigin: $countryOfOrigin, language: $language) {
            ... on LotV2 {
                ...LotInfoFragment
            }
        }

    }
    
    fragment LotInfoFragment on LotV2 {
        description
    }
"""

def get_lot_id_query():
    return LOT_ID_QUERY

def get_lot_description_query():
    return LOT_DESCRIPTION_QUERY