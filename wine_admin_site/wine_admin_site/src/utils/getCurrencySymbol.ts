const getCurrencySymbol = (currency?: string) => {
    switch (currency?.toUpperCase()) {
      case 'USD':
        return '$';
      case 'EUR':
        return '€';
      case 'GBP':
        return '£';
      case 'HKD':
        return 'HK$';
      case 'JPY':
        return '¥';
      case 'CNY':
        return '¥';
      case 'CHF':
        return 'CHF ';
      case 'AUD':
        return 'A$';
      case 'CAD':
        return 'C$';
      default:
        return currency + ' ';
    }
}

export default getCurrencySymbol;