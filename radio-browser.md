# PyRadio RadioBrowser Implementation

[RadioBrowser](https://www.radio-browser.info/) is "a community driven effort (like wikipedia) with the aim of collecting as many internet radio and TV stations as possible."

**PyRadio** uses the API provided to integrate it and provide its users the possibility to enjoy this great project.

**Note:** As of the writing of this (v. **0.8.9.4**, which should actually be called ***0.9-beta1***), the implementation is not yet complete, but it is usable (accessing and querying the service is up and running). Whenever a feature is not implemented yet, it will be explicitly marked as such.

## Table of Contents
<!-- vim-markdown-toc Marked -->

* [Opening RadioBrowser](#opening-radiobrowser)
* [Closing RadioBrowser](#closing-radiobrowser)
* [How it works](#how-it-works)
    * [Searching in the list of stations](#searching-in-the-list-of-stations)
    * [Sorting stations](#sorting-stations)
* [Controls](#controls)
* [Configuration](#configuration)
* [Station Database Information](#station-database-information)
* [Station clicking and voting](#station-clicking-and-voting)
* [Server Selection](#server-selection)
* [Search Window](#search-window)
    * [Search term composition](#search-term-composition)
    * [History Management](#history-management)

<!-- vim-markdown-toc -->
[[Return to main doc]](README.md)

## Opening RadioBrowser

To open **RadioBrowser** one would just press "**O**" at the program's main window. Since at this point this is the only service supported, the service will be activated.


![Pyradio's RadioBrowser interface](https://members.hellug.gr/sng/pyradio/pyradio-radio-browser.png)

Upon activation, the **default query** will be preformed and (if successful) its results will be presented to the user. If unsuccessful, a relevant message will be displayed and the program will return to the local playlist that was previously opened.

By default, **PyRadio** will load the first 100 most voted stations on **RadioBrowser**. 

## Closing RadioBrowser

**PyRadio** treats the service as a special kind of a playlist, thus to close the service it is enough to "*go back to playlist history*", pressing "**\\\\**" (double backslash), in addition to the normal way ("**q**" or **Escape**).

## How it works

The implementation uses a list structure (we'll call it "**search history**" from now on) to keep user specified queries (we'll call them "**search terms**").

The first item in the "**search history**" is the "**empty search term**" (or "**empty item**"), which cannot be deleted and cannot be used to actually query **RadioBrowser**; it is there to provide a "**search term template**" for user inserted search terms.

Upon activation, the "**default search term**" is used to automatically query a randomly selected **RadioBrowser** server and display stations' results.

Once the results are fetched, they act as a special kind of playlist (some of the features of a local playlist are not functional, such as station renaming and such), and other features are introduced (such as the sort function and the station database info function).

Each search result, i.e. each station, has more data attached to it than just its name and URL (bitrate, votes, clicks, etc.). This data is displayed in field columns; the number of visible columns depend on the terminal of the window. The name of the column that matches the sorting criteria is "highlighted".

### Searching in the list of stations

The normal local playlist search function has been enhanced in order to be able to search through the list of stations, since each station has a lot more info attached to it.

Searching for any string will return matches in the "**Name**" field only (just like in a local playlist), but starting the search string with a plus sign ("**+**") will produce results from all available fields (visible or not).

### Sorting stations

Pressing "**S**" will present the user with a sorting list. Selecting one of the items will sort the stations based on it; selecting it again will reverse sorting order.

**Note:** This sorting function is different than the query sorting criterion which can be selected in the [Search window](#search-window). This one just sorts a query result set, the one in the "**Search window**" affects the actual stations that will be in the result set.

## Controls

These are the **RadioBrowser** specific keys one can use in addition to local playlist keys (if applicable).

| Key           | Action                                    |
|---------------|-------------------------------------------|
| O             | Open RadioBrowser                         |
| c             | Open config window                        |
| C             | Select server to connect to               |
| s             | Search for stations                       |
| S             | Sort search results                       |
| I             | Station database info (current selection) |
| V             | Vote for station                          |
| \\\\ q Escape | Close RadioBrowser                        |


## Configuration

This feature has not been implemented yet.

## Station Database Information

The database information of the selected station can be displayed by pressing "**I**". Keep in mind that, this is different than the "Station ino" displayed by pressing "**i**" (lowercase "i"), which is still available and presents live data.

## Station clicking and voting

**RadioBrowser** provides two ways to measure a station's popularity: voting and clicking.

**Clicking** a station means that the station has been listened to; **PyRadio** will send a "click request" any time the user starts playback of a station; **RadioBrowser** will either reject or accept the action, and either ignore or increase click count for the station based on several criteria (time between consecutive clicks, possibly IP, etc.) 

For this reason **PyRadio** will in no case adjust the click count presented to the user.

**Voting** for a station is a different thing; the user has to choose to vote for it. In **PyRadio** a "vote request" is sent when "**V**" is pressed. If the vote has been accepted, the vote counter will be increased by one.

**Note:** Inconsistencies between a voted for station's local vote counter value and the one reported in a consecutive server response should be expected, since it seems servers' vote counter sync may take some time to complete.

## Server Selection

**RadioBrowser** provides several servers to the public (currently in Germany, France and The Netherlands), which are constantly kept in sync. Its API provides a way to "discover" these servers and then select the one to use.

**PyRadio** will randomly select one of these servers and will display its location in its window title.

Pressing "**C**" will provide a list of available servers to choose from. This selection will be honored until the service is closed.

## Search Window

The "**Search window**" opens when "**s**" is pressed and loads the "**search term**" that was used to fetch the stations currently presented in the "**RadioBrowser window**". If this is the first time this window is opened within this session, the search term that's loaded is the "**default search term**".

**Note:** In case the server returns no results, the window will automatically reopen so that you can redefine the "**search term**".

Navigation between the various fields is done using the "**Tab**" (and "**Shift-Tab**") key, the arrows and **vim keys** ("**j**", "**k**", "**h**" and "**l**"), provided that any given key is not already used by one of the on window "widgets".

![RadioBrowser Search Window](https://members.hellug.gr/sng/pyradio/radio-browser-search-window.png)

This window performs two functions: 

1) composes a search term to be forwarded to the search function and 
2) manages the "**search history**".


### Search term composition

The "**Search window**" can be divided in four parts:

- The "**Display**" part

    In this part one would select to fetch a list of stations based on a single criterion such as their vote count, click count, etc.

- The "**Search**" part

    In this part, the user would insert a search string to one or more of the available fields.

    Each of the fields has an "**Exact**" checkbox. If checked, an exact match will be returned, hopefully.

    In the "**Country**" field one could either provide the name of a country or its two-letter code (based on [ISO 3166](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2)). For example, to get a list of Greek stations, you would either insert "*greece*" or the country code, which is "*gr*".

These two parts are mutually exclusive, since when one is activated through its corresponding checkbox, the other one gets disabled.

- The "**Sort**" part

    This part affects both previous parts.

    It provides the server with the sorting criteria upon which the results will be returned.

- The "**Limit**" part

    In this part the maximum number or returned stations is specified. The default value is 100 stations (0 means no limit).

    The value can be changed using the left and right arrows or "**h**", "**l**" and "**PgUp**", "**PgDn**" for a step of 10.

### History Management

At the bottom of the "**Search window**" you have the **history information**  section; on the left the number of history items is displayed along with the number of the current history item ("**search term**") and on the right there's the history help legend.

The keys to manage the history are all **Control** combinations:

|Key            |Action                                                |
|---------------|------------------------------------------------------|
|**^N** **^P**  |Move to next / previous "**search term**" definition. |
|**^Y**         |Move to the "**empty search term**" (history item 0). This is a quick way to "reset" all settings and start new. Of course, one could just navigate to this history item using **^N** or **^P**, but it's here just for convenience.|
|**^T**        |Add current item to history.|
|**^X**        |Delete the current history item.<br>There is no confirmation and once an item is deleted there's no undo function.<br>These rules apply:<br> 1. The first item (**search term template**) cannot be deleted.<br>2. When the history contains only two items (the **search term template** will always be the first one; the second one is a user defined **search term**), no item deletion is possible.<br>3. When the **default search term** is deleted, the first user defined **search term** becomes the default one.|
|**^B**        |Make the current history item the **default** one for **RadioBrowser** and save the history.<br>This means that, next time you open **RadioBrowser** this history item ("**search term**") will be automatically loaded.|
|**^V**        |Save the history.|

All movement actions (**^N**, **^P**, **^Y**) will check if the data currently in the "form" fields can create a new **search term** and if so, will add it to the history.

The **Search Window** actually works on a copy of the **search history** used by the service itself, so any changes made in it (adding and deleting items) are not passed to the service, until "**OK**" is pressed. Pressing "**Cancel**" will make all the changes go away.

Even when "**OK**" is pressed, and the "**Search Window**" is closed, the "new" history is loaded into the service, but NOT saved to the *configuration file*.

To really save the "new" history, press "**^V**" in the **Search Window**, or press "**y**" in the confirmation window upon exiting the service.
