import pandas
import plotnine
import streamlit

import wrapped


metrics = [
    'words',
    'fics',
    'reads'
]

figures = [
    'titles',
    'authors',
    'relationships',
    'characters',
    'tags'
]


streamlit.title('AO3 wrapped')

streamlit.markdown("""
Inspired by and adapted from the work of the amazing [bothermione](https://www.bothermione.com/wrapped)!

**No, you probably shouldn't enter your username and password into a random webpage, so don't actually use this. It's just for me.**

---
""")

progress_container = streamlit.empty()

username = streamlit.sidebar.text_input('username')
password = streamlit.sidebar.text_input('password', type='password')

valid_user = False

if username and password:
    
    with progress_container.container():
        streamlit.caption('fetching results...')

    try:
        response = wrapped.resolve_request(username, password)
        valid_user = True
    except wrapped.InvalidUserOrPasswordError:
        with progress_container.container():
            streamlit.caption('Invalid username or password.')

if valid_user:

    results = wrapped.analysis(response)

    streamlit.subheader(username)

    for metric, col in zip(metrics, streamlit.columns(len(metrics))):
        with col:
            streamlit.metric(f'total {metric}', results[f'total_{metric}'])
    
    for name, tab in zip(figures, streamlit.tabs(figures)):
        with tab:

            data = pandas.DataFrame(results['most_visited'][name], columns=[name, 'count'])

            if not data.empty:

                data[name] = pandas.Categorical(
                    data[name],
                    categories=reversed(data[name].tolist())
                )

                fig = (
                    plotnine.ggplot(data)
                    + plotnine.aes(
                        x=name,
                        y='count',
                        label='count'
                    )
                    + plotnine.labs(x='')
                    + plotnine.geom_col()
                    + plotnine.geom_text()
                    + plotnine.coord_flip()
                )

                streamlit.pyplot(fig.draw())
            
            else:
                streamlit.markdown('**none!**')
    
    with progress_container.container():
        streamlit.caption('done!')

streamlit.markdown("""
---

See the source code for this app [here](https://github.com/pickleherring/ao3-wrapped-app).
""")
