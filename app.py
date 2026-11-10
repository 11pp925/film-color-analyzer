import io
import csv
from collections import Counter

import numpy as np
import streamlit as st
from PIL import Image, ImageOps, ImageDraw, ImageFont

st.set_page_config(page_title='Film Color Analyzer', page_icon='🎬', layout='wide')
st.title('🎬 Film Color Analyzer')
st.caption('영화 색채 분석 도구 | Explore the dominant colors in a film still')
st.write('Upload a film still to discover its dominant colors, their proportions, and a downloadable palette.')

with st.sidebar:
    st.header('Settings')
    n_colors = st.slider('Number of dominant colors', 3, 8, 5)
    st.info('Colors are estimated from sampled pixels. The result describes the image, not the director’s intent.')

uploaded = st.file_uploader('Upload a film screenshot (JPG or PNG)', type=['jpg', 'jpeg', 'png'])


def rgb_hex(rgb):
    return '#%02X%02X%02X' % tuple(int(v) for v in rgb)


def make_palette(colors):
    w, sw, h = 1000, 1000 // len(colors), 230
    canvas = Image.new('RGB', (w, h), 'white')
    draw = ImageDraw.Draw(canvas)
    for i, (rgb, pct) in enumerate(colors):
        left = i * w // len(colors)
        right = (i + 1) * w // len(colors)
        draw.rectangle([left, 0, right, 165], fill=tuple(rgb))
        draw.text((left + 10, 180), rgb_hex(rgb), fill='black')
        draw.text((left + 10, 203), f'{pct:.1f}%', fill='black')
    output = io.BytesIO()
    canvas.save(output, format='PNG')
    return output.getvalue()


if uploaded is not None:
    try:
        source = Image.open(uploaded)
        image = ImageOps.exif_transpose(source).convert('RGB')
        image.thumbnail((1600, 1600))
        st.subheader('Uploaded image')
        st.image(image, use_container_width=True)

        sample = image.copy()
        sample.thumbnail((350, 350))
        # Median-cut quantization: fast, deterministic, and does not need an API.
        quantized = sample.quantize(colors=n_colors, method=Image.Quantize.MEDIANCUT)
        palette = quantized.getpalette()
        counts = Counter(quantized.getdata())
        total = sum(counts.values())
        colors = []
        for idx, count in counts.most_common(n_colors):
            rgb = tuple(palette[idx * 3:idx * 3 + 3])
            colors.append((rgb, count * 100 / total))

        st.subheader('Dominant color palette')
        cols = st.columns(len(colors))
        for col, (rgb, pct) in zip(cols, colors):
            with col:
                hex_value = rgb_hex(rgb)
                st.markdown(f'<div style="height:90px;background:{hex_value};border-radius:9px;border:1px solid #aaa"></div>', unsafe_allow_html=True)
                st.markdown(f'**{hex_value}**')
                st.caption(f'{pct:.1f}%')

        st.subheader('Color distribution')
        st.bar_chart({rgb_hex(rgb): pct for rgb, pct in colors}, horizontal=True)

        pixels = np.asarray(sample, dtype=np.float32).reshape(-1, 3)
        avg = pixels.mean(axis=0)
        mean_brightness = float((0.2126 * pixels[:, 0] + 0.7152 * pixels[:, 1] + 0.0722 * pixels[:, 2]).mean())
        # Warm/cool is only a simple RGB heuristic, not a scientific mood classification.
        warm_score = float(np.mean(pixels[:, 0] - pixels[:, 2]))
        if warm_score > 12:
            temperature = 'Warmer (more red than blue overall)'
        elif warm_score < -12:
            temperature = 'Cooler (more blue than red overall)'
        else:
            temperature = 'Relatively balanced red/blue'
        brightness = 'Bright' if mean_brightness >= 170 else ('Dark' if mean_brightness < 85 else 'Medium brightness')
        st.subheader('Simple visual observations')
        st.write(f'**Color tendency:** {temperature}')
        st.write(f'**Overall brightness:** {brightness} ({mean_brightness:.0f}/255)')
        st.caption('These are simplified numerical observations. Color meaning depends on narrative and context.')

        png = make_palette(colors)
        st.download_button('⬇️ Download palette PNG', png, file_name='film_color_palette.png', mime='image/png')
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(['HEX', 'R', 'G', 'B', 'Percent'])
        for rgb, pct in colors:
            writer.writerow([rgb_hex(rgb), *rgb, f'{pct:.2f}'])
        st.download_button('⬇️ Download color data CSV', csv_buffer.getvalue(), file_name='film_colors.csv', mime='text/csv')
    except Exception as exc:
        st.error(f'Unable to analyze this image: {exc}')
else:
    st.info('Upload an image above to begin the analysis.')

st.divider()
st.caption('Built with Python, Streamlit, Pillow, and NumPy. No API key required.')
