library(readxl)
require(tidyverse)
library(shiny)

raw_data <- read_excel("portugal_apartments.xlsx")

data_province <- raw_data |>
  filter(Rooms_num != "more") |>
  mutate(Rooms_num = ifelse(Rooms_num == "zero", 0, Rooms_num)) |>
  mutate(Rooms_num = as.numeric(Rooms_num)) |>
  filter(!is.na(Rooms_num)) |>
  mutate(Area = as.numeric(Area)) |>
  filter(!is.na(Area)) |>
  filter(Area < 300 & Price & 5000000 & hidePrice == "0") |>
  mutate(filter_auxiliar_area = ifelse(Area < 30 & Rooms_num != 0, "delete", "ok")) |>
  filter(filter_auxiliar_area == "ok") |>
  filter(Area > 15) |>
  select(c(Area, Bathrooms_num, Construction_year, Energy_certificate, Province,
           Rooms_num, Price, Condition)) |>
  mutate(Construction_year = as.numeric(Construction_year ),
  )|>
  filter(Construction_year > 1920 & Construction_year <= 2023) |>
  filter_all(all_vars(!is.na(.))) |>
  mutate(Energy_certificate = ifelse(Energy_certificate =="bminus",
                                     "b", ifelse(Energy_certificate == "aplus", "a", Energy_certificate)))|>
  mutate(Bathrooms_num = as.factor(Bathrooms_num),
         Energy_certificate = as.factor(Energy_certificate),
         Province = as.factor(Province),
         Condition = as.factor(Condition))

locations<- unique(data_province$Province)

lm_model_province <- lm(Price ~ ., data = data_province)

# Save model to file

saveRDS(lm_model_province, file = "cloud_deployment/lm_model_province.rds")
