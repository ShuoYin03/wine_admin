CREATE TABLE IF NOT EXISTS auctions (
    Id SERIAL PRIMARY KEY,
    External_Id TEXT UNIQUE,
    Auction_Title VARCHAR(255),
    Auction_House VARCHAR(255),
    City VARCHAR(100),
    Continent VARCHAR(100),
    Start_Date DATE,
    End_Date DATE,
    Year INT,
    Quarter INT,
    Auction_Type VARCHAR(50),
	Url TEXT
);

CREATE TABLE IF NOT EXISTS lots (
    Id SERIAL PRIMARY KEY,
    External_Id TEXT UNIQUE,
    Auction_Id TEXT REFERENCES auctions(External_Id) ON DELETE CASCADE,
    Lot_Name VARCHAR(150),
    Lot_Type VARCHAR(8)[],
    Volume REAL,
    Unit INT,
    Original_Currency VARCHAR(10),
    Start_Price INT,
    End_Price INT,
	Low_Estimate INT,
	High_Estimate INT,
    Sold BOOLEAN,
    Sold_Date DATE,
    Region VARCHAR(20),
	Sub_Region VARCHAR(50),
    Country VARCHAR(20),
	Success BOOLEAN,
	Url TEXT
);

CREATE TABLE IF NOT EXISTS lot_items (
    Id SERIAL PRIMARY KEY,
    Lot_Id TEXT REFERENCES lots(External_Id) ON DELETE CASCADE,
    Lot_Producer VARCHAR(50),
    Vintage VARCHAR(20),
    Unit_Format VARCHAR(20),
    Wine_Colour VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS auction_sales (
    id SERIAL PRIMARY KEY,
    Auction_Id TEXT REFERENCES auctions(External_Id) ON DELETE CASCADE UNIQUE,
    Lots INT,
    Sold INT,
    Currency VARCHAR(10),
    Total_Low_Estimate INT,
    Total_High_Estimate INT,
    Total_Sales INT,
    Volume_Sold REAL,
    Value_Sold REAL,
    Top_Lot TEXT,
    Sale_Type VARCHAR(50),
    Single_Cellar BOOLEAN,
    Ex_Ch BOOLEAN
);

CREATE TABLE IF NOT EXISTS lwin_database (
    id INT PRIMARY KEY,
    Lwin INT,
    Status TEXT,
    Display_Name TEXT,
    Producer_Title TEXT,
    Producer_Name TEXT,
    Wine TEXT,
    Country TEXT,
    Region TEXT,
    Sub_Region TEXT,
    Site TEXT,
    Parcel TEXT,
    Colour TEXT,
    Type TEXT,
    Sub_Type TEXT,
    Designation TEXT,
    Classification TEXT,
    Vintage_Config TEXT,
    First_Vintage INT,
    Final_Vintage INT,
    Date_Added TIMESTAMP,
    Date_Updated TIMESTAMP,
    Reference TEXT
);

CREATE TABLE IF NOT EXISTS lwin_matching (
    id SERIAL PRIMARY KEY,
    Lot_Id TEXT REFERENCES lots(External_Id) ON DELETE CASCADE,
    Matched TEXT,
    Lwin INT[],
    Lwin_11 BIGINT[],
    Match_Item JSONB,
    Match_Score DOUBLE PRECISION[]
);

CREATE TABLE IF NOT EXISTS fx_rates_cache (
    id SERIAL PRIMARY KEY,
    Rates_From VARCHAR(10),
    Rates_To VARCHAR(10),
    Date DATE,
    Rates DOUBLE PRECISION
);