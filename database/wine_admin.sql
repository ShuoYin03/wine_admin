CREATE TABLE IF NOT EXISTS auctions (
    id TEXT PRIMARY KEY,
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
    id TEXT PRIMARY KEY,
    Auction_Id TEXT,
    Lot_Producer VARCHAR(50)[],
    Wine_Name VARCHAR(150),
    Vintage VARCHAR(20)[],
    Unit_Format VARCHAR(20)[],
	Unit INT,
	Volumn REAL,
	Lot_Type VARCHAR(8)[],
	Wine_Type VARCHAR(8),
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

CREATE TABLE IF NOT EXISTS failed_lots (
    id TEXT PRIMARY KEY,
    Auction_Id TEXT,
    Lot_Producer VARCHAR(50)[],
    Wine_Name VARCHAR(150),
    Vintage VARCHAR(20)[],
    Unit_Format VARCHAR(20)[],
	Unit INT,
	Volumn REAL,
	Lot_Type VARCHAR(8)[],
	Wine_Type VARCHAR(8),
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

CREATE TABLE IF NOT EXISTS auction_sales (
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
    Vintage TEXT,
    First_Vintage INT,
    Final_Vintage INT,
    Date_Added DATETIME,
    Date_Updated DATETIME,
    Reference INT
);

CREATE TABLE IF NOT EXISTS lwin_matching (
    lot_id TEXT PRIMARY KEY,
    Matched TEXT,
    Lwin INT[],
);