# Sell That Sheet API

---

```mermaid
erDiagram
    PHOTO {
        int id PK "Unique identifier"
        string name "Name of the photo"
    }
    PHOTOSET {
        int id PK "Unique identifier"
        string directoryLocation "Directory location on server"
        int thumbnailPhotoId FK "Thumbnail photo"
    }
    AUCTION {
        int id PK "Unique identifier"
        string name "Auction name"
        float pricePLN "Price in PLN"
        float priceEuro "Price in Euro"
        string tags "Tags"
        string serialNumbers "Serial numbers"
        int photoSetId FK "Associated PhotoSet"
    }
    AUCTIONSET {
        int id PK "Unique identifier"
        string directoryLocation "Directory location on server"
    }
    PARAMETER {
        int id PK "Unique identifier"
        string allegro_id "Allegro parameter ID"
        string name "Parameter name"
        string type "Parameter type"
    }
    AUCTION_PARAMETER {
        int id PK "Unique identifier"
        int parameterId FK "Associated Parameter"
        string valueName "Parameter Value name"
        string valueId "Parameter Value id"
    }
    
    PHOTOSET ||--o{ PHOTO : contains
    PHOTOSET ||--|| PHOTO : "has thumbnail"
    AUCTION ||--|| PHOTOSET : "has"
    AUCTIONSET ||--o{ AUCTION : contains
    PARAMETER ||--o{ AUCTION_PARAMETER: "instance of"
    AUCTION_PARAMETER }o--|| AUCTION: "contains"
```
 
