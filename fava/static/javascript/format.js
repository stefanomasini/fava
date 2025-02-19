// Helper functions to format numbers and dates.

import { format } from "d3-format";
import { utcFormat } from "d3-time-format";

import e from "./events";
import { favaAPI } from "./stores";

let formatter;
let incognito;

e.on("page-init", () => {
  const { locale } = favaAPI.favaOptions;
  if (locale) {
    formatter = new Intl.NumberFormat(locale.replace("_", "-")).format;
  } else {
    formatter = format(".2f");
  }
  if (favaAPI.incognito) {
    incognito = num => num.replace(/[0-9]/g, "X");
  } else {
    incognito = num => num;
  }
});

export function formatCurrency(number) {
  return incognito(formatter(number));
}

const formatterPer = format(".2f");
export function formatPercentage(number) {
  return `${formatterPer(Math.abs(number) * 100)}%`;
}

const formatterShort = format(".2s");
export function formatCurrencyShort(number) {
  return incognito(formatterShort(number));
}

export const dateFormat = {
  year: utcFormat("%Y"),
  quarter(date) {
    return `${date.getUTCFullYear()}Q${Math.floor(date.getUTCMonth() / 3) + 1}`;
  },
  month: utcFormat("%b %Y"),
  week: utcFormat("%YW%W"),
  day: utcFormat("%Y-%m-%d"),
};

export const timeFilterDateFormat = {
  year: utcFormat("%Y"),
  quarter(date) {
    return `${date.getUTCFullYear()}-Q${Math.floor(date.getUTCMonth() / 3) +
      1}`;
  },
  month: utcFormat("%Y-%m"),
  week: utcFormat("%Y-W%W"),
  day: utcFormat("%Y-%m-%d"),
};
