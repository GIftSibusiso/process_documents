from flask import Flask, request, jsonify, make_response
import pandas as pd

from io import BytesIO

app = Flask(__name__)

ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/data', methods=['POST'])
def get_data():
    if 'dataset_file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    
    file = request.files['dataset_file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file.stream)
            else:
                df = pd.read_excel(file.stream)
            
            data = df.to_dict(orient='records')
            
            return jsonify({
                'message': 'Data extracted successfully',
                'records_processed': data,
            })
            
        except pd.errors.EmptyDataError:
            return jsonify({'error': 'The file is empty or corrupt'}), 400
        except Exception as e:
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    else:
        return jsonify({'error': 'File type not allowed. Please upload .xlsx, .xls, or .csv files.'}), 400



@app.route('/export-data', methods=['POST'])
def export_data():
    try:
        flattened_data = request.json.get('data', [])

        if not flattened_data:
            return jsonify({'error': 'No data to export'}), 400
        
        df = pd.DataFrame(flattened_data)
        
        df.columns = [col.replace('-', ' ').title() for col in df.columns]
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Submissions', index=False)
            
            workbook = writer.book
            worksheet = writer.sheets['Submissions']
            
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, max_len)
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=parent_submissions.xlsx'
        
        return response
        
    except Exception as e:
        app.logger.error(f"Export error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to generate export. Please try again later.'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0')
