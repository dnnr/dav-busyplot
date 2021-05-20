#!/usr/bin/env python3

import argparse
import bokeh as bk
import bokeh.plotting as bkp
import os
import pandas as pd
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta
from collections import OrderedDict

OPENING_HOURS = ('10:30', '21:00')


def load_data(db_path):
    with sqlite3.connect(db_path) as db:
        df = pd.read_sql_query("SELECT datetime,present FROM bergwelt",
                               db,
                               parse_dates={'datetime': {"format": '%Y-%m-%d %H:%M:%S'}})

    # Fix UTC (TODO: Fix this at the source):
    df['datetime'] += timedelta(hours=2)

    df.set_index("datetime", inplace=True)

    return df


def make_figure_all_time(df):
    """ Return a bokeh figure plotting the visitor numbers over time. """
    figure = bkp.figure(
        x_axis_type='datetime',
        sizing_mode='stretch_width',
        title="Visitors (all time)",
        x_axis_label='Time',
        y_axis_label='People present',
        tools='xpan,xbox_zoom,reset,save,xwheel_zoom',
        active_scroll='xwheel_zoom',
        y_range=bk.models.DataRange1d(start=0),
    )

    figure.xaxis.formatter = bk.models.formatters.DatetimeTickFormatter(
        days=['%Y-%m-%d, %a'],
    )

    color_mapper = bk.models.LinearColorMapper(palette=list(reversed(bk.palettes.Plasma[11])), low=0, high=65)

    span = 30
    span_str = f'{span}min'
    vbar_width_factor = 0.8

    span_max = df.resample(span_str).max()
    span_max.index = span_max.index.shift(0.5, freq=span_str)

    # Hack: Add .1 so that zero is visible (distinguishable from no data)
    #  span_max += .1
    # TODO: Make zero-values during opening hours more visible, somehow

    figure.vbar(x='datetime', top='present', source=span_max, width=vbar_width_factor * span * 60 * 1000, alpha=1, color={'field': 'present', 'transform': color_mapper})

    # Add color bar legend:
    color_bar = bk.models.ColorBar(color_mapper=color_mapper,
                         ticker=bk.models.BasicTicker(desired_num_ticks=len(color_mapper.palette)),
                         formatter=bk.models.PrintfTickFormatter(format="%d"))
    figure.add_layout(color_bar, "right")

    return figure


def make_figure_weekly_heatmap(df):
    """ Return bokeh figure showing a heat map for each day, grouped by weeks. """

    ###
    # Some behavioral parameters
    ###
    # Interval length to quantize data into (in minutes)
    resample_span_minutes = 30

    # Height of each vbar (percentage)
    vbar_height = 0.8

    # X-axis padding between the hours
    subgroup_padding = 0.2

    # X-axis padding between the vbar within an hour
    factor_padding = 0.2

    # X-axis padding between days of the week
    group_padding = 2

    # X-axis padding between all the data and the visible area
    range_padding = .05

    # Resample data into the maximum of each interval, shift values to be
    # centered within the intervals:
    span_str = f'{resample_span_minutes}min'
    df = df.resample(span_str).max()
    df.index = df.index.shift(0.5, freq=span_str)

    # Invalidate all data outside of opening hours
    not_before = datetime.strptime(OPENING_HOURS[0], '%H:%M').time()
    not_after = datetime.strptime(OPENING_HOURS[1], '%H:%M').time()
    df.drop((index for index in df.index if index.time() < not_before or index.time() > not_after), inplace=True)

    # Add column that holds the ISO calender week number (stringified in order
    # to plot it as category, not integer)
    df['weeknum'] = df.index.isocalendar().week.apply(str)

    # Compute weektime column that holds as tuple representing the time
    # relative to the beginning of the week. Using strftime ensures that values
    # are strings, which is what we need to plot the x-axis as categorical
    # data, instead of an actual timeline with night hours and all.
    df['weektime'] = [(datetime.strftime(index, '%A'),
                       index.time().strftime('%H'),
                       index.time().strftime('%H:%M'),
                       )
                      for index in df.index]

    # Explicitly define all values for the x-axis in order. Otherwise, the axis
    # would start where the input data starts, which is not necessarily Monday
    # morning.
    x_range = []
    for weekday in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"):
        opening_times = pd.date_range(start='10:45', end='21:00', freq='30min')
        for time in opening_times:
            hour_string = time.strftime('%H')
            time_string = time.strftime('%H:%M')
            x_range.append((weekday, hour_string, time_string))

    figure = bkp.figure(
        sizing_mode='stretch_width',
        title="Visitor heatmap by week",
        x_axis_label='Time of week',
        y_axis_label='Calendar week',
        tools='ypan,ywheel_zoom,reset,save',
        active_scroll='ywheel_zoom',
        x_range=bk.models.FactorRange(factors=x_range,
                                      factor_padding=factor_padding,
                                      subgroup_padding=subgroup_padding,
                                      group_padding=group_padding,
                                      range_padding=range_padding,
                                      ),
        y_range=bk.models.FactorRange(factors=list(reversed(OrderedDict.fromkeys(df['weeknum'])))),
    )

    figure.xaxis.major_label_orientation = 1

    color_mapper = bk.models.LinearColorMapper(palette=list(reversed(bk.palettes.Plasma[11])), low=0, high=65)

    # Draw each time slice as a rectangle
    figure.rect(x='weektime', y='weeknum', source=df,
                width=1,
                height=vbar_height,
                alpha=1,
                color={'field': 'present', 'transform': color_mapper},
                )

    # Add color bar legend:
    color_bar = bk.models.ColorBar(color_mapper=color_mapper,
                         ticker=bk.models.BasicTicker(desired_num_ticks=len(color_mapper.palette)),
                         formatter=bk.models.PrintfTickFormatter(format="%d"))
    figure.add_layout(color_bar, "right")

    # Hide all grid lines:
    figure.xgrid.grid_line_color = None
    figure.ygrid.grid_line_color = None

    return figure


def run(args):
    argparser = argparse.ArgumentParser()
    argparser.add_argument('db', type=str)
    argparser.add_argument('outdir', type=str)
    argparser.add_argument('--filename', default='dav-busyplot.html', type=str)
    argparser.add_argument('--use-cdn', action='store_true')
    args = argparser.parse_args(args)

    if not args.use_cdn:
        # Set rootdir so that bokeh.min.js is loaded from the same directory as the
        # HTML file:
        bk.settings.settings.rootdir = os.path.join(bk.util.paths.ROOT_DIR, 'server/static/js')
        bk.settings.settings.resources = 'relative'

        shutil.copyfile(os.path.join(bk.settings.settings.rootdir(), 'bokeh.min.js'),
                        os.path.join(args.outdir, 'bokeh.min.js'))

    df = load_data(args.db)

    figure_all_time = make_figure_all_time(df.copy())
    figure_weekly_heatmap = make_figure_weekly_heatmap(df)

    # Set a dummy height value for each figure (without it, the auto-sizing in layouts doesn't work)
    figure_all_time.height = 42
    figure_weekly_heatmap.height = 42
    figure_all_time.sizing_mode = 'stretch_both'
    figure_weekly_heatmap.sizing_mode = 'stretch_both'

    #  plot = bk.layouts.gridplot([[figure_all_time], [figure_all_time2]], sizing_mode='stretch_both')
    plot = bk.layouts.column([figure_all_time, figure_weekly_heatmap], sizing_mode='stretch_both')

    bkp.output_file(os.path.join(args.outdir, args.filename),
                    title='DAV busy plot')
    bkp.save(plot)


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
