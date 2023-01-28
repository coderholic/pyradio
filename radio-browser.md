# PyRadio RadioBrowser Implementation

[RadioBrowser](https://www.radio-browser.info/) is "a community driven effort (like wikipedia) with the aim of collecting as many internet radio and TV stations as possible."

**PyRadio** uses the API provided to integrate it and provide its users the possibility to enjoy this great project.

**Note:** As of the writing of this, the implementation is not yet complete, but it is usable (accessing and querying the service is up and running). Whenever a feature is not implemented yet, it will be explicitly marked as such.

## Table of Contents
<!-- vim-markdown-toc Marked -->

* [Opening RadioBrowser](#opening-radiobrowser)
* [Closing RadioBrowser](#closing-radiobrowser)
* [How it works](#how-it-works)
    * [Searching in the list of stations](#searching-in-the-list-of-stations)
    * [Sorting stations](#sorting-stations)
* [Controls](#controls)
* [Configuration](#configuration)
    * [Server pinging](#server-pinging)
* [Server Selection](#server-selection)
* [Station Database Information](#station-database-information)
* [Station clicking and voting](#station-clicking-and-voting)
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

**Note:** One would get this information using the program's help (pressing "**?**" and navigating to the last page of it).

## Configuration

One can get to **RadioBrowser**'s configuration in any of the following ways:

1. From PyRadio **Configuration**, section **Online Services**

2. From within **RadioBrowser** playlist, by pressing "*c*"

The configuration window presents the following options:

1. **Auto save config**\
If True, no confirmation will be asked before saving  the configuration when leaving the search window.\
Default value: *False*

2. **Maximum number of results**\
**RadioBrowser**'s database is really huge and some queries will produce too many results. This is the way to limit returned result number.\
Setting this parameter to -1 will disable result limiting.\
Default value: *100*

3. **Number of ping packages**\
The number of ping (ICMP) packages to send to a server while checking its availability. More on "*Server pinging*" later in this section.\
A value of 0 will disable server pinging.\
Default value: *1*

4. **Ping timeout (seconds)**\
The number of seconds to wait for a ping command to terminate while checking a server's availability.\
A value of 0 will disable server pinging.\
Default value: *1*

5. **Default Server**\
The default server to connect to when using the service.\
Default value: *Random*

6. **Search Terms**\
User defined "*Search Terms*" displayed in a compact way. \
Available actions: change the **default** search term and **delete** existing search terms.

### Server pinging

**RadioBrowser** currently provides a network of 3 servers to connect to (always kept in sync with each other), in order to limit down time.

In the rare event an individual server is down, an application can just connect to any of the remaining servers to keep using the service.

**PyRadio** will use the ICMP protocol (ping) to check servers availability before even trying to query a server. The configuration  parameters  "*Number
of ping packages*" and "*Ping timeout (seconds)*" will be used to ping the servers. If any of them is set to 0, **server pinging will be disabled.**

When opening the service, **PyRadio** will act depending upon its configured settings.

1. **No default server is specified and pinging is enabled**\
In this case, **PyRadio** will randomly select a server, make sure it's online (ping it) and then use it to query and display results.\
If no server is available or if the internet connection has failed, a message will be displayed informing the user.

2. **A default server has been specified and pinging is enabled**\
**PyRadio** will ping the server and will connect to it if it's available.\
If the default server is unresponsive, **PyRadio** will try to find and use one that is available.\
If no server is available or if the internet connection has failed, a message will be displayed informing the user.

3. **Pinging is disabled**\
No server availability check will occur.\
If the server (default or random) is unavailable or if the internet connection has failed, a message will be displayed informing the user.

When using the "**Server Selection Window**" (either within the configuration window or the playlist):

1. **If pinging is enabled**\
The selected server availability will be checked, and if not responsive, it will not be accepted.

2. **If pinging is disabled**\
The server will be accepted regardless of its availability.

## Server Selection

In addition to the "*default server*" which can be set at the configuration window, one has the possibility to select a server to connect after opening the service.

Pressing "**C**" will provide a list of available servers to choose from. This selection will be honored until the service is closed.

## Station Database Information

The database information of the selected station can be displayed by pressing "**I**". Keep in mind that, this is different than the "Station ino" displayed by pressing "**i**" (lowercase "i"), which is still available and presents live data.

## Station clicking and voting

**RadioBrowser** provides two ways to measure a station's popularity: voting and clicking.

**Clicking** a station means that the station has been listened to; **PyRadio** will send a "click request" any time the user starts playback of a station; **RadioBrowser** will either reject or accept the action, and either ignore or increase click count for the station based on several criteria (time between consecutive clicks, possibly IP, etc.)

For this reason **PyRadio** will in no case adjust the click count presented to the user.

**Voting** for a station is a different thing; the user has to choose to vote for it. In **PyRadio** a "vote request" is sent when "**V**" is pressed. If the vote has been accepted, the vote counter will be increased by one.

**Note:** Inconsistencies between a voted for station's local vote counter value and the one reported in a consecutive server response should be expected, since it seems servers' vote counter sync may take some time to complete.

## Search Window

The "**Search window**" opens when "**s**" is pressed and loads the "**search term**" that was used to fetch the stations currently presented in the "**RadioBrowser window**". If this is the first time this window is opened within this session, the search term that's loaded is the "**default search term**".

**Note:** In case the server returns no results, the window will automatically reopen so that you can redefine the "**search term**".

Navigation between the various fields is done using the "**Tab**" (and "**Shift-Tab**") key, the arrows and **vim keys** ("**j**", "**k**", "**h**" and "**l**"), provided that any given key is not already used by one of the on window "widgets".

Toggling the state of check boxes is done by pressing **SPACE**. The "*Display by*" and "*Search for*" check boxes are mutually exclusive (enabling one disables the other). Each of them will give access to more fields when enabled.

To perform a search (server query) one would just press **Enter** on the "**OK**" button, or "**s**" on any widget other than a *Line editor*.

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
|**HOME** or **0**  |Move to the "**empty search term**" (history item 0), the *template item*. This is a quick way to "reset" all settings and start new. Of course, one could just navigate to this history item using **^N** or **^P**, but it's here just for convenience.<br><br>Pressing **0** works on all widgets; **HOME** does not work on **Line editors**.<br>To inster a **0** on a **Line editor** just type "**\0**".|
|**END** or **g** or **&dollar;**  |Move to the last **search term**.<br><br>Pressing **&dollar;** works on all widgets; **END** and **g** do not work on **Line editors**.<br>To inster a **&dollar;** on a **Line editor** just type "**\\&dollar;**".||
|**PgUp** / **PgDown**|Jump up or down within the "**search history**" list.<br>These keys do not work when the "*Result limit*" counter field is focused.|
|**^Y**        |Add current item to history.|
|**^X**        |Delete the current history item.<br>There is no confirmation and once an item is deleted there's no undo function.<br>These rules apply:<br> 1. The first item (**search term template**) cannot be deleted.<br>2. When the history contains only two items (the **search term template** will always be the first one; the second one is a user defined **search term**), no item deletion is possible.<br>3. When the **default search term** is deleted, the first user defined **search term** becomes the default one.|
|**^B**        |Make the current history item the **default** one for **RadioBrowser** and save the history.<br>This means that, next time you open **RadioBrowser** this history item ("**search term**") will be automatically loaded.|
|**^E**        |Save the history.|

**Note:** All keys can also be used without pressing the Control key, provided that a line editor does not have the focus. For example, pressing "**x**" is the same as pressing "**^X**", "**e**" is the same as "**^E**" and so on. This feature is provided for tiling window manager users who may have already assigned actions to any of these Contol-key combinations.

All history navigation actions (**^N**, **^P**, **HOME**, **END**, **PgUp**, **PgDown**) will check if the data currently in the "form" fields can create a new **search term** and if so, will add it to the history.

The **Search Window** actually works on a copy of the **search history** used by the service itself, so any changes made in it (adding and deleting items or changing the default item) are not passed to the service, until "**OK**" is pressed (or "**s**" is typed on any field other than a "*Line editor*"). Pressing "**Cancel**" will make all the changes go away.

Even when "**OK**" (or "**s**" is typed on any field other than a "*Line editor*") is pressed, and the "**Search Window**" is closed, the "new" history is loaded into the service, but NOT saved to the *configuration file*.

To really save the "new" history, press "**^E**" in the **Search Window** (or "**e**" is typed on any field other than a "*Line editor*"), or press "**y**" in the confirmation window upon exiting the service.
