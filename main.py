import os
import re
import random
import pickle

import discord
from discord.ext import commands

import skybox_fetcher

pages_dir = 'pages/'
frames_dir = 'frames/'
gif_dir = 'gif/'
database_file = 'database.txt'

#https://discordapp.com/api/oauth2/authorize?client_id=569075344938893322&permissions=261184&scope=bot
with open(os.path.abspath("token.txt"), "r") as f:  # 261184
    TOKEN = f.read()

bot = commands.Bot(command_prefix=('$', '!'))

current_page = 1
current_frame = -1
current_gif = 2

last_invoked = None

now_downloading = False

data = None
arcs_names = None


async def _download():
    global now_downloading, arcs_names, data
    if not now_downloading:
        now_downloading = True
        downloaded = await skybox_fetcher.pull_comic()

        now_downloading = False
        arcs_names, data = None, None
        return downloaded


@bot.event
async def on_ready():
    print('Logged in as {}'.format(bot.user))
    print(bot.guilds)


@bot.event
async def on_message(message):
    #print(message.guild.name, message.channel.name, str(message.author).split('#')[1])
    if message.guild is not None:
        if message.guild.name == "The Skybox" and message.channel.name == "newest-updates" and str(message.author).split('#')[1] == '8517':
            print("Message from Lynx! New updates!")
            await message.add_reaction(emoji="👍")
            await _download()
            await message.add_reaction(emoji="✅")

    await bot.process_commands(message)


@bot.command()
async def hello(ctx):
    variants = \
        ["Hi, {}!",
         "Skybox waited for you, {}!",
         "Greetings, {} =)",
         "/-//- /--/ {}",
         "Oh! Hello there, you must be {}!",
         "G'day, {}!",
         "Howdy, {}",
         ]
    name = discord.ext.commands.HelpCommand().remove_mentions(ctx.author.display_name)
    await ctx.send(random.choice(variants).format(name))


@bot.command()
async def download(ctx):
    async with ctx.typing():
        if not now_downloading:
            await ctx.send("Download process started!")
            downloaded = await _download()
            await ctx.send("Downloaded and split {} new frames and {} new gif animations!".format(*downloaded))
        else:
            await ctx.send("Comic downloading process is already running, just hang out a bit!")


def _get_database(database=database_file):
    global data, arcs_names
    if (data is None) or (arcs_names is None):
        with open(os.path.abspath(database), 'rb') as f:
            file_arc_names, file_data = pickle.load(f)

        data = file_data
        arcs_names = file_arc_names

    return arcs_names, data


@bot.command()
async def arc(ctx, *args):
    args = list(args)
    arcs, dt = _get_database()
    frame = None
    is_gif = False
    try:
        if args[0].isdigit():
            arc = arcs[int(args[0].lstrip("0") or 0)]
        else:
            if args[0].lower() == 'im':
                arc = arcs[0]
            else:
                arc = args[0].lower().capitalize()

        if len(args) >= 2:
            if not args[1].isdigit():
                args.pop(1)
            page = args[1].zfill(2)

            if len(args) >= 3:
                if not args[2] in ("gif", "-gif", "--gif"):
                    if not args[2].isdigit():
                        args.pop(2)
                    frame = int(args[2].lstrip("0"))-1
                else:
                    is_gif = True
        else:
            page = "Title"
        result = dt[(arc, page)]
    except (KeyError, ValueError, IndexError):
        async with ctx.typing():
            await ctx.send("Seems there is some mistakes in command! Maybe such page is missing!")

    else:
        with ctx.typing():
            if frame is not None:
                if frame+1 > result[1]:
                    await ctx.send("Frame number is out of range")
                else:
                    ind = result[0]-result[1]+frame
                    img = '{}.jpg'.format(ind)
                    try:
                        file = discord.File(os.path.abspath(frames_dir + img), filename=img)
                    except FileNotFoundError:
                        await ctx.send("Sorry, but i can't find such frame!")
                    else:
                        await ctx.send("Here you go, frame №{} of Arc {} - {}: Page {} - frame {}/{}".format(
                            ind,
                            arcs_names.index(arc),
                            arc,
                            page,
                            frame+1,
                            result[1],
                        ), file=file)
            else:
                ind = list(dt.keys()).index((arc, page))+2
                if is_gif:
                    img = '{}.gif'.format(ind)
                    try:
                        file = discord.File(os.path.abspath(gif_dir + img), filename=img)
                    except FileNotFoundError:
                        await ctx.send("Sorry, but i can't find such gif!")
                    else:
                        await ctx.send("Here you go, gif №{} of Arc {} - {}: Page {} ({} frames)".format(
                            ind,
                            arcs_names.index(arc),
                            arc,
                            page,
                            result[1],
                        ), file=file)
                else:
                    img = '{}.jpg'.format(ind)
                    try:
                        file = discord.File(os.path.abspath(pages_dir + img), filename=img)
                    except FileNotFoundError:
                        await ctx.send("Sorry, but i can't find such page!")
                    else:
                        await ctx.send("Here you go, page №{} of Arc {} - {}: Page {} ({} frames)".format(
                            ind,
                            arcs_names.index(arc),
                            arc,
                            page,
                            result[1],
                        ), file=file)


@bot.command()
async def page(ctx, arg1):
    global current_page

    arcs, dt = _get_database()

    if arg1 in ("random", "rnd"):
        paths = os.listdir(os.path.abspath(pages_dir))
        img = random.choice(paths)
        current_page = int(img.split('.')[0])

    else:
        if arg1 in ("next", "forward", "+1"):
            current_page += 1
        elif arg1 in ("previous", "back", "-1"):
            current_page -= 1
        else:
            try:
                current_page = int(arg1)
            except ValueError:
                await ctx.send("Hey, that should be a page *number*! Integer, ya know")
                return
        img = '{}.jpg'.format(current_page)

    item = list(dt.items())[current_page-2]

    async with ctx.typing():
        try:
            file = discord.File(os.path.abspath(pages_dir + img), filename=img)
        except FileNotFoundError:
            await ctx.send("Sorry, but i can't find such page!")
        else:
            await ctx.send("Here you go, page №{} of Arc {} - {}: Page {} ({} frames)".format(
                current_page,
                arcs_names.index(item[0][0]),
                item[0][0],
                item[0][1],
                item[1][1],
            ), file=file)


@bot.command()
async def frame(ctx, arg1):
    global current_frame

    arcs, dt = _get_database()

    if arg1 in ("random", "rnd"):
        paths = os.listdir(os.path.abspath(frames_dir))
        img = random.choice(paths)
        current_frame = int(img.split('.')[0])
    else:
        if arg1 in ("next", "forward", "+1"):
            current_frame += 1
        elif arg1 in ("previous", "back", "-1"):
            current_frame -= 1
        else:
            try:
                current_frame = int(arg1)
            except ValueError:
                await ctx.send("Hey, that should be a frame *number*! Integer, ya know")
                return
        img = '{}.jpg'.format(current_frame)

    for i, fr in enumerate([x[0] for x in list(dt.values())]):
        if current_frame+1 <= fr:
            page = i
            break

    item = list(dt.items())[page]

    async with ctx.typing():
        try:
            file = discord.File(os.path.abspath(frames_dir + img), filename=img)
        except FileNotFoundError:
            await ctx.send("Sorry, but i can't find such frame!")
        else:
            await ctx.send("Here you go, frame №{} of Arc {} - {}: Page {} - frame {}/{}".format(
                current_frame,
                arcs_names.index(item[0][0]),
                item[0][0],
                item[0][1],
                item[1][1] - (item[1][0] - current_frame) + 1,
                item[1][1],
            ), file=file)


@bot.command()
async def gif(ctx, arg1):
    global current_gif

    arcs, dt = _get_database()

    if arg1 in ("random", "rnd"):
        paths = os.listdir(os.path.abspath(gif_dir))
        img = random.choice(paths)
        current_gif = int(img.split('.')[0])

    else:
        if arg1 in ("next", "forward", "+1"):
            current_gif += 1
        elif arg1 in ("previous", "back", "-1"):
            current_gif -= 1
        else:
            try:
                current_gif = int(arg1)
            except ValueError:
                await ctx.send("Hey, that should be a gif *number*! Integer, ya know")
                return
        img = '{}.gif'.format(current_gif)

    async with ctx.typing():
        try:
            file = discord.File(os.path.abspath(gif_dir + img), filename=img)
        except FileNotFoundError:
            await ctx.send("Sorry, but i can't find such gif!")
        else:
            if current_gif > 2:
                item = list(dt.items())[current_gif - 2]

                await ctx.send("Here you go, gif №{} of Arc {} - {}: Page {} ({} frames)".format(
                    current_gif,
                    arcs_names.index(item[0][0]),
                    item[0][0],
                    item[0][1],
                    item[1][1],
                ), file=file)
            else:
                await ctx.send("Here you go, bonus gif №{}".format(current_gif), file=file)

@bot.command()
async def spacetalk(ctx, *args):
    input_msg = " ".join(args).lower()
    out_msg = re.sub('[aeiou]', '-', input_msg)
    out_msg = re.sub('--', '—', out_msg)
    out_msg = re.sub('[b-df-hyj-np-tv-xz]', '/', out_msg)

    await ctx.send("`{}`".format(out_msg))  # Some spaceside once told me:


@bot.command()
async def database(ctx):
    async with ctx.typing():
        try:
            file = discord.File(os.path.abspath(database_file), filename=database_file)
        except FileNotFoundError:
            await ctx.send("Sorry, but i can't find mah database!")
        else:
            await ctx.send("Here you go, my full database!", file=file)


bot.run(TOKEN.strip())

# list(mydict.keys())[list(mydict.values()).index(somevalue)]
