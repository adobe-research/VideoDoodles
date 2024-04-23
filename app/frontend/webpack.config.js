const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const path = require('path');

const mode = process.env.NODE_ENV || 'development';
const prod = mode === 'production';
const dev = !prod;

module.exports = {
	entry: {
		bundle: ['./src/main.js']
	},
	resolve: {
		alias: {
			svelte: path.resolve('node_modules', 'svelte')
		},
		extensions: ['.mjs', '.js', '.svelte'],
		mainFields: ['svelte', 'browser', 'module', 'main']
	},
	output: {
		path: __dirname + '/public',
		filename: '[name].js',
		chunkFilename: '[name].[id].js'
	},
	module: {
		rules: [
            {
                test: /\.svelte$/,
                use: {
                  loader: 'svelte-loader',
				  options: {
					onwarn: (warning, handler) => {
						if (warning.code === 'a11y-click-events-have-key-events') return
					
						// Handle all other warnings normally
						handler(warning)
					},
				  }
                //   options: {
                //     dev,
                //     hotReload: true,
                //     hotOptions: {
                //       // whether to preserve local state (i.e. any `let` variable) or
                //       // only public props (i.e. `export let ...`)
                //       noPreserveState: false,
                //       // optimistic will try to recover from runtime errors happening
                //       // during component init. This goes funky when your components are
                //       // not pure enough.
                //       optimistic: true,
        
                //       // See docs of svelte-loader-hot for all available options:
                //       //
                //       // https://github.com/rixo/svelte-loader-hot#usage
                //     },
                //   },
                },
              },
			{
				test: /\.css$/,
				use: [
					/**
					 * MiniCssExtractPlugin doesn't support HMR.
					 * For developing, use 'style-loader' instead.
					 * */
					prod ? MiniCssExtractPlugin.loader : 'style-loader',
					'css-loader'
				]
			},
			{
				test: /\.obj$/,
				use: [
					'raw-loader'
				]
			},
			{
				test: /\.(glsl|vs|fs|vert|frag)$/,
				exclude: /node_modules/,
				use: [
				  'raw-loader',
				  'glslify-loader'
				]
			}
		]
	},
	mode,
	plugins: [
		new MiniCssExtractPlugin({
			filename: '[name].css'
		})
	],
	resolve: {
        fallback: {
          fs: false
        }
      },
	devtool: prod ? false: 'source-map',
    devServer: {
        // contentBase: 'public',
        hot: true,
        // overlay: true,
      },
};