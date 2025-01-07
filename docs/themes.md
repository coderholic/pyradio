# PyRadio Themes

## Table of Contents
<!-- vim-markdown-toc Marked -->

* [PyRadio Themes](#pyradio-themes)
    * [Virtual terminal restrictions](#virtual-terminal-restrictions)
        * [Workaround for not supported terminals](#workaround-for-not-supported-terminals)
    * [CSS color themes restrictions](#css-color-themes-restrictions)
    * [Secondary windows background](#secondary-windows-background)
        * [Theme defined secondary windows color](#theme-defined-secondary-windows-color)
        * [Calculated secondary windows color](#calculated-secondary-windows-color)
            * [Optional Calculated Color in a Theme](#optional-calculated-color-in-a-theme)
    * [Alternative Main Window border color](#alternative-main-window-border-color)
    * [User themes](#user-themes)
        * [Converting old themes](#converting-old-themes)
    * [Using transparency](#using-transparency)
    * [Updating themes automatically](#updating-themes-automatically)
    * [Using Project Themes](#using-project-themes)
        * [base16](#base16)
            * [Using the themes without base16](#using-the-themes-without-base16)
        * [pywal](#pywal)
        * [theme.sh](#theme.sh)
            * [Using the themes without theme.sh](#using-the-themes-without-theme.sh)

<!-- vim-markdown-toc -->

[ [Return to main doc](index.md#pyradio-themes) ]

## PyRadio Themes

**PyRadio** comes with 6 preconfigured (hard coded) themes:

1. **dark** (8 color theme). \
This is the appearance **PyRadio** has always had. Enabled by default.
2. **light** \
A theme for light terminal background settings.
3. **dark_16_colors** \
"**dark**" theme alternative.
4. **light_16_colors** \
"**light**" them alternative.
5. **white_on_black** or **wob** (b&w theme). \
A theme for dark terminal background settings.
6. **black_on_white** or **bow** (b&w theme). \
A theme for light terminal background settings.

Furthermore, a number of themes (these are actual files saved in the **themes** installation directory) are also available:

- **AM_by_amski1** \
A simple green on dark theme, created for Windows.
- **blue-by-boxer** \
A reddish on blue theme by user **Boxer** at [Mabox Forum](https://forum.maboxlinux.org/).
- **catppuccin-frappe**, **catppuccin-latte**, **catppuccin-macchiato** and **catppuccin-mocha** \
Four themes by the [Catppuccin community](https://github.com/catppuccin).
- **classic_by_obsdg** \
A clasic theme by [The OpenBSD Guy](https://github.com/OpenBSDGuy), originally created on [OpenBSD](https://www.openbsd.org/).
- **cupcake_by_edunfelt** and  **fairyflossy_by_edunfelt** \
Two themes by [edunfelt](https://github.com/edunfelt) inspired by the [base16](https://github.com/base16-project) project.
- **dracula_by_Plyply99** \
A theme based of the Dracula theme by [Plyply99](https://github.com/Plyply99).
- everforest-hard.pyradio-theme
A theme by [CabalCrow](https://github.com/CabalCrow) based on [Everforest](https://github.com/sainnhe/everforest), "a green based color scheme; it's designed to be warm and soft in order to protect developers' eyes."
- *gruvbox_dark_by_farparticul*, **gruvbox_dark_by_sng** and **gruvbox_light_by_sng** \
Three themes based on the [gruvbox](https://github.com/morhetz/gruvbox) theme.
- **hyprland_amber_gold** and **hyprland_dracula** \
Two themes by [mechatour](https://github.com/mechatour), from [hyprland_amber_gold](https://github.com/mechatour/hyprland_amber_gold) and [hyprland_dotfiles]([https://github.com/mechatour/hyprland_dotfiles).
- **lambda_by_amski1** \
A light theme by user [amski1](https://forum.maboxlinux.org/u/amski1).
- **minima_by_ben_chile** \
A theme by user [ben_chile](https://forum.maboxlinux.org/u/ben_chile) created on the [Mabox Linux](https://maboxlinux.org) Forum.
- **pastel_based_by_sng** \
A dim but colorful theme.

Contrary to the old styling method, which was terminal and palette dependent, a new styling method has been implemented; actual CSS colors can now be defined.

Theme sample / template:

```
# Main foreground and background
Stations            #8b8198 #fbf1f2

# Playing station text color
# (background color will come from Stations)
Active Station      #d57e85

# Status bar foreground and background
Status Bar          #fbf1f2 #d57e85

# Normal cursor foreground and background
Normal Cursor       #fbf1f2 #dcb16c

# Cursor foreground and background
# when cursor on playing station
Active Cursor       #fbf1f2 #d57e85

# Cursor foreground and background
# This is the Line Editor cursor
Edit Cursor         #fbf1f2 #bfb9c6

# Text color for extra function indication
# and jump numbers within the status bar
# (background color will come from Stations)
Extra Func          #69a9a7

# Text color for URL
# (background color will come from Stations)
PyRadio URL         #a3b367

# Message window border foreground and background.
# The background color can be left unset.
# Please refer to the following link for more info
# https://github.com/coderholic/pyradio#secondary-windows-background
#
Messages Border     #a3b367

# Theme Transparency
# Values are:
#   0: No transparency
#   1: Theme is transparent
#   2: Obey config setting (default)
transparency        0
```

Pressing "**t**" will bring up the *Theme selection window*, which can be used to activate a theme and set the default one.

**Note:** If the theme selected in the "*Theme selection window*", (or requested using the "**-t**" command line option), is in any way invalid, or is of the old format, **PyRadio** will fall-back to the "**dark**" theme and will display a relevant message.

The window will display the current state of the **Use transparency** and **Force transparency** configuration options in its bottom right corner:

- A **[T]** means that the **Use transparency** option is enabled.
- A **[F]** means that the **Force transparency** option is enabled.
- A **[TF]** means that the both options are enabled.

One can get more info about these options in the "[Using Transparency](#using-transparency)" section, bellow.

**Note:** the options indication will not be visible when the window is opened withing the **PyRadio**'s "*Configuration Window*".

The "*Theme selection window*" will remain open after activating a theme, so that the user can inspect the visual result and easily change it, if desired. Then, when he is satisfied with the activated theme, the window will have to be manually closed (by pressing "**q**" or any other relevant key - pressing "**?**" will bring up its help).

Pressing "**SPACE**", will apply the theme and make it default, and pressing "**c**" will apply the theme and make it default and start a file watch function on the file, so that if the file changes, **PyRadio** will automatically update itself.

### Virtual terminal restrictions

After introducing CSS color themes, it has come to my attention that **PyRadio** will not display colors correctly when executed within specific terminals, *konsole*, *yakuake*, *deepin-teminal*, *qterminal* and *terminology*, just to name a few.

Now, I do not know whether this is because of the terminals themselves, python curses implementation or whatever, but that's that.

**PyRadio** will try to detect these terminals and disable themes (after displaying a relative message). Then the default theme will be used.

Some of the terminals that work ok, are: *gnome-terminal*, *mate-terminal*, *xfce4-terminal*, *lxterminal*, *terminator*, *termite*, *kitty*, *alacritty*, *sakura*, *roxterm*, *tilix*, *lilyterm*, *st*, *xst*, *rxvt*, *urxvt*, *uxterm*, *xterm*.

If you want to make **PyRadio** start in one of these terminal, just follow the instructions given at [Desktop File: Specifying the terminal to use](#specifying-the-terminal-to-use).

#### Workaround for not supported terminals

Thanks to github user [troyvit](https://github.com/troyvit), it is now possible to use **PyRadio** with full color support on most of the terminals that originally will not display colors correctly.

Following his [report](https://github.com/coderholic/pyradio/issues/254), which proposes to execute **PyRadio** within a [tmux](https://github.com/tmux/tmux/wiki) session, a [bash srciprt](https://gist.github.com/s-n-g/2f1ef5c764222d26e5bb0075b2adddb1) has been written to accomplish the task: it is called "**tmux_pyradio**" and comes in the form of a github gist.

Using "**tmux_pyradio**" on can execute **PyRadio** in any terminal (it has been tested in all the terminals referenced above); one can even run a second **PyRadio** instance throught it. For more info, download it and execute:

    tmux_pyradio -h

There is a catch though; if **PyRadio** terminates prematurely, the output will not be visible to the user, since **tmux** will also terminate and clear the screen on exit. In this case, just add a "*-d*" before a "*--*" (or combine it with the custom tmux session name). Yhis will add a *pause* before exiting **tmux**, so you can observe the output.

### CSS color themes restrictions

Using CSS colors imposes a couple of restrictions on the type of terminals **PyRadio** will be able to run:

1. The TERM variable must be set *(Linux and MacOs only)*. \
\
**PyRadio** will set it to "*xterm-256color*" if not set. \
\
Furthermore, if TERM is set to anything like "**xterm**", "**screen**" or "**tmux**", **PyRadio** will set it to "*xterm-256color*" as well.

2. Terminals that do not support at least 16 colors will not be able to display any of the new themes. The same goes for terminals that do not support changing their colors (through the **curses** library). \
\
These terminal will default to either the "**dark**" or the "**light**" theme (determined by the configuration parameter **console_theme**), displaying whatever colors the active palette dictates.

3. There are a couple of terminals (that I know of) which will permit changing their colors but will not be able to present the changed color on the fly. \
\
This means that, in order for a theme change to take full effect, **PyRadio** will have to be restarted.

### Secondary windows background

Secondary windows (such as messages, questions, the "*Theme Selection window*" the "*Encoding Selection window*", etc.) originally use the same background color as the "*Main window*".

It is now possible to use a different background color for these windows, to get better visual result.

There are two way to do that:

1. Defined in a theme

2. Using a calculated color

#### Theme defined secondary windows color

Themes have the following entry

```
# Message window border foreground and background.
# The background color can be left unset.
# Please refer to the following link for more info
# https://github.com/coderholic/pyradio#secondary-windows-background
#
Messages Border     #a3b367
```

It is possible to define a background color as well, like so


```
Messages Border     #a3b367 #F5DBDE
```

In this case, this color will be used as the Secondary Windows background color.

Although one can use any color here, it is recommended to follow these guidelines for best visual result:

1. The color should be 1-20% lighter or darker than the "*Stations Background*" color setting of the theme. \
\
One can use [this page](http://www.workwithcolor.com/hsl-color-picker-01.htm) (or a similar one) to insert the base color and adjust the "*L*" component as needed. \
\
A terminal alternative is [pastel](https://github.com/sharkdp/pastel), which can be used like so:

```
pastel color '#fbf1f2'              # show color info
pastel lighten .1 '#fbf1f2'         # color lightened by 10%
pastel darken .1 '#fbf1f2'          # color darkened by 10%
```


2. If the "*Stations Background*" color is dark, create a lighter version of it; if it's light, create a darker version of it. \
\
This is just a recomenration, though; just get a color that combines well with existing ones (border foreground, stations foreground and active station).

This information is actually relevant to creating a new **PyRadio** theme, but it's very important in order to understand how the calculated background color works.

#### Calculated secondary windows color

**PyRadio** will use the same background color for all windows by default, provided that the theme used does not define a "*Messages Border*" **background color**.

In order to use a "*Messages Border*" background color different than the "*Stations background*" color, when "*Messages Border*" background color is not defined in the selected theme, a config option is available; "**Calculated color**".

This config option takes a value that's between 0 and 0.2.

If it is 0, no color change will occur.

Otherwise, the value acts as a percentage (a **factor**), which indicates how much the luminance of the "*Stations background*" color will change to produce the new background color.

This is how this works: **PyRadio** will calculate the "*Stations background*" color perceived brightness, which will indicate whether the color is dark or light. Then depending on that, will add or subtract **factor** percent from its luminance value.

Finally, a check will be made to see if this color is close to "*Messages Border*" foreground color, and re-adjusted as possible.

**Note:** When a calculated background color is used, pressing "**~**" (**tilde**) will toggle it on and off. This setting will be valid until **PyRadio** terminates, or a new theme is loaded.

##### Optional Calculated Color in a Theme

Another way to use a different background color for secondary windows, is to provide one in the actual theme file. For example:

```
# Luminance Color Factor
# The factor to lighten or darken Stations background
# color, to get a calculated color used as background
# for secondary windows
# Valid values: 0 - 0.2
Color Factor        0.05
```

In this case, the value provided (i.e. 0.05) will be used the same way as the config option **Calculated color**.

In fact, if both a theme and a config factor value is provided, the value provided by the theme will be used.

**Note:** If the "**Messages Border**" theme option provides both a foreground and a background, both the *calculated* values provided will be ignored.

### Alternative Main Window border color

It is also possible to change the **Main Window** border color. This is a feature that has been requested and implemented, but not used by default.

To provide an alternative border color, one would just add the following to a theme file:

```
# Border color for the Main Window
# (background color will come from Stations)
Border              #69a9a7
```

**Note:** This color will be used **only** when the terminal supports more than 16 colors. This is because **Pyradio** already uses colors 0-15, and this border color will be declared as color No 16.

### User themes

Users can easiliy create their own themes, using for example [CSS color names](https://www.cssportal.com/css3-color-names/) as a resource, and

1. Save the theme provided as a template above in their themes folder using any (short) file name and a "**.pyradio-theme**" file extension. \
\
For this reason, a folder called "**themes**" will probably have to be created in **PyRadio** config directory (**~/.config/pyradio** or **%APPDATA%\\pyradio** on Windows)


2. Customize it as desired

3. Load it from the "*Theme selection window*" (it will be found under "**User Themes**").


#### Converting old themes

An old theme (using the old format) can be asily converted to the new format, using the script found at [this gist](https://gist.github.com/s-n-g/65aa6ae12e135481bf3a503ece4e92d2).

**Note:** In order to get the color intended to be used, the same palette as the one used when the original theme was created, must be used.

### Using transparency

For **PyRadio**, transparency means that a theme's background actually disappears, effectively making it to display whatever is on the terminal (color/picture/transparency).  The visual result depends on terminal settings and whether a compositor is running.

Not all themes look good when transparency is ON, so themes can now declare whether they want to use transparency or not. This is the "**transparency**" variable of the theme, which can have these values:

- 0 means that the theme will be opaque (no transparency)
- 1 means that the theme will be transparent
- 2 means that the theme looks good either way (the default), and the global transparency setting value (defined in **PyRadio** config file) will be used.

Please note that this behavior has changed since **v. 0.9.2.7**: theme transparency will always be honored, regardless of the global config value.

This means that a theme which is set to be transparent (by its creator) will always be transparent, no matter if the global transparency is on or off. Similarly, if a theme is set to be opaque, it will be so regardless of the global transparency value.

The only case when global transparency will come into play is when the theme does not care about it (theme transparency set to 2 - Obey config setting).

Since **v. 0.9.2.14**, it is also possible to **force** the use of the Transparency setting; the "**Force Transparency**" configuration option. When enabled, it will effectively make all themes behave as if their **transparency** setting was set to 2 (Obey config setting).

The following table illustrates how things work:

|  Force transparency  | Theme setting               | PyRadio honors   | If Config Transparency<br>is ON, you get  | If Config Transparency is OFF, you get
|  --------------------| ----------------------------| ----------------------| ---------------------------------------| ----------------------------------------
|  False<br>(the default)               | 0 - Do not use transparency  | Theme setting         | Opaque window                                    | Opaque window
|                      | 1 - Theme is transparent    | Theme setting         | Transparent window                                     | Transparent window
|                      | 2 - Don\'t care             | Config Transparency          | Transparent window                                     | Opaque window
|  True                | Any (0, 1 or 2)             | Config Transparency          | Transparent window                                     | Opaque window

So, pressing "**T**" when **Force Transparency** is enabled, or the theme's **transparency** value is set to 2, will toggle the window's transparency.

### Updating themes automatically

Terminal users have been using all kind of software to change / update / adapt their terminal colors and palettes, such as [bASE16](https://github.com/chriskempson/base16), [pywal](https://github.com/dylanaraps/pywal), [wpgtk](https://github.com/deviantfero/wpgtk), [theme.sh](https://github.com/lemnos/theme.sh), to name a few.

**PyRadio** is now able to "watch" a given theme for changes and update its colors whenever the theme changes.

To set up a theme for auto update, one would just open the "*Theme Selection*" window, navigate to a theme under "**User Themes**" and press "**c**". To create a **user theme** just follow the procedure described in section [User themes](#user-themes).

Consecuently, the default theme name will be preceded by:

- "**\***" if the theme is the default one (the way it has always been).
- "**+**" if the theme is the default one, and **PyRadio** will watch it for changes.

### Using Project Themes

**PyRadio** is able to use (and watch) the output of certain projects that modify terminal colors.

**PyRadio** will detect theses projects (programs installed and initialized), and will add them under the "**Ext. Themes Projects**" section of the "*Themes Selection Window*."

If loading any of these themes fails, the default **dark** theme will be loaded, but contrary to a local theme being invalid, the selection will persist (so that the theme gets loaded wheneve it is available).

Currently, the following projects are supported:

#### base16

Thanks to the wonderful work by user [edunfelt](https://github.com/edunfelt), there is now a **PyRadio** [base16](https://github.com/base16-project) template in place, and themes have been produced based on the project (there are more than 900 themes available).

This implementation will add four entries in the theme selection menu (with alternative and variant forms of the main theme).

Then, any of the themes can either be activated or watched; in which case **PyRadio** will download and apply the corresponding theme.

##### Using the themes without base16

In case one wants to use any of these themes, but not install or use [base16](https://github.com/base16-project), one can get them [from this repo](https://github.com/edunfelt/base16-pyradio), and use the "*cycle_themes.py*" and "*install_themes.py*" scripts to inspect and install them.

For Windows users, this is the only way to use any of these "*Project Themes*", since their generation works on non-windows platforms only.

#### pywal

When detected, two themes will be added to the menu; the main and the alternative form.

Since these themes are generated on the fly, as the wallpaper changes, there is no way to use them if [pywal](https://github.com/dylanaraps/pywal) is not in use.

**Note:** If [pywal](https://github.com/dylanaraps/pywal) themes are activated but not watched, the theme will be corrupted when the wallpaper changes, and will have to be manually reloaded. So, it's better to just always watch these themes.

#### theme.sh

When detected, four themes will be added to the menu; the main and the alternative forms (there are 400 plus themes available, which makes a stuggering number of around 1800 themes for **PyRadio**!)

##### Using the themes without theme.sh

In case one wants to use any of these themes, but not install or use [theme.sh](https://github.com/lemnos/theme.sh), one can download [this repo](https://github.com/s-n-g/theme-sh-pyradio), and use the "*create_themes.py*" script to create the themes, and "*cycle_themes.py*" and "*install_themes.py*" scripts to inspect and install them.

For Windows users, this is the only way to use any of these "*Project Themes*", since their generation works on non-windows platforms only.

