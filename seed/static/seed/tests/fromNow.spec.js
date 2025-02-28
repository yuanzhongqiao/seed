/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 *
 * tests fromNow angularjs filter wrapper of moment.js
 * uses epoch milliseconds as that is what the back-end returns
 */

// create dummy angularJS app to attach filter(s)
const myfromNowFilterApp = angular.module('myfromNowFilterApp', ['fromNow']);

describe('The fromNow filter', () => {
  let fromNowFilter;

  beforeEach(() => {
    module('myfromNowFilterApp');
    inject((_fromNowFilter_) => {
      fromNowFilter = _fromNowFilter_;
    });
  });

  it('shows the present time as "a few seconds ago"', () => {
    // arrange
    const date_epoch_mills = new Date().getTime();

    // act
    const from_now_value = fromNowFilter(date_epoch_mills);

    // assert
    expect(from_now_value).toBe('a few seconds ago');
  });

  it('shows 5 minutes ago as "5 minutes ago"', () => {
    // arrange
    let date_epoch_mills = new Date().getTime();
    date_epoch_mills -= 5 * 60 * 1000;

    // act
    const from_now_value = fromNowFilter(date_epoch_mills);

    // assert
    expect(from_now_value).toBe('5 minutes ago');
  });

  it('shows 4 hours ago as "4 hours ago"', () => {
    // arrange
    let date_epoch_mills = new Date().getTime();
    date_epoch_mills -= 4 * 60 * 60 * 1000;

    // act
    const from_now_value = fromNowFilter(date_epoch_mills);

    // assert
    expect(from_now_value).toBe('4 hours ago');
  });

  it('shows 24 hours ago as "a day ago"', () => {
    // arrange
    let date_epoch_mills = new Date().getTime();
    date_epoch_mills -= 24 * 60 * 60 * 1000;

    // act
    const from_now_value = fromNowFilter(date_epoch_mills);

    // assert
    expect(from_now_value).toBe('a day ago');
  });

  it('shows 36 hours ago as "2 days ago"', () => {
    // arrange
    let date_epoch_mills = new Date().getTime();
    date_epoch_mills -= 36 * 60 * 60 * 1000;

    // act
    const from_now_value = fromNowFilter(date_epoch_mills);

    // assert
    expect(from_now_value).toBe('2 days ago');
  });

  it('shows 1550 hours ago as "2 months ago"', () => {
    // arrange
    let date_epoch_mills = new Date().getTime();
    date_epoch_mills -= 1550 * 60 * 60 * 1000;

    // act
    const from_now_value = fromNowFilter(date_epoch_mills);

    // assert
    expect(from_now_value).toBe('2 months ago');
  });

  it('defaults to "a few seconds ago" for undefined values', () => {
    // arrange

    // act

    // assert
    expect(fromNowFilter(undefined)).toBe('a few seconds ago');
    expect(fromNowFilter(null)).toBe('a few seconds ago');
    expect(fromNowFilter('some text')).toBe('a few seconds ago');
    expect(fromNowFilter({})).toBe('a few seconds ago');
    expect(fromNowFilter({ time: 'not time' })).toBe('a few seconds ago');
  });
});
