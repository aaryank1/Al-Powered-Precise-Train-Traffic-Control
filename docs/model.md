# Model v1 : 

We have a single-track railway line:

    Virar ---- Bhayandar ---- Borivali ---- Andheri ---- Bandra ---- Dadar

There is only one track.

| Station   | Platform Count |
| --------- | -------------- |
| Virar     | 1              |
| Bhayandar | 1              |
| Borivali  | 1              |
| Andheri   | 1              |
| Bandra    | 1              |
| Dadar     | 1              |

## Loop Lines

Without loop lines, trains coming in opposite directions would deadlock.

So we introduce loops at: Borivali and Andheri

    Virar ---- Bhayandar ---- Borivali ---- Andheri ---- Bandra ---- Dadar
                                LOOP          LOOP

## Train Types and Priority

LOCAL = 1,
FAST = 5,
EXPRESS = 10

EXPRESS > FAST > LOCAL