CREATE TABLE IF NOT EXISTS Auction (
    id TEXT PRIMARY KEY,
    Auction_Title VARCHAR(255),
    Auction_House VARCHAR(255),
    City VARCHAR(100),
    Continent VARCHAR(100),
    Start_Date DATE,
    End_Date DATE,
    Year INT,
    Quarter INT,
    Auction_Type VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS Lot (
    id TEXT PRIMARY KEY,
    AuctionId TEXT,
    Lot_Producer VARCHAR(255),
    Lot_Wine_Name VARCHAR(255),
    Lot_Vintage INT,
    Lot_Unit_Format VARCHAR(100),
    Lot_Unit INT,
    Original_Currency VARCHAR(10),
    Lot_Start_Price INT,
    Lot_End_Price INT,
    Lot_Sold BOOLEAN,
    Lot_Region VARCHAR(50),
    Lot_Country VARCHAR(50),
    FOREIGN KEY (AuctionId) REFERENCES Auction(id)
);

CREATE TABLE IF NOT EXISTS AuctionSales (
    id TEXT PRIMARY KEY,
    Lots INT,
    Sold INT,
    Currency VARCHAR(10),
    Total_Low_Estimate INT,
    Total_High_Estimate INT,
    Total_Sales INT,
    Volumn_Sold VARCHAR(50),
    Value_Sold VARCHAR(50),
    Top_Lot TEXT,
    Sale_Type VARCHAR(50),
    Single_Cellar BOOLEAN,
    Ex_Ch BOOLEAN,
    FOREIGN KEY (Top_Lot) REFERENCES Lot(id)
);