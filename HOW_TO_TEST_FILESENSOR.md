# 🔍 How to Test FileSensor

You now have two simple FileSensor DAGs to learn with:

## 📁 **DAG 1: file_sensor_simple**
**Automatic file creation and processing**

### How it works:
1. **create_test_file** - Creates a test file automatically
2. **wait_for_file** - FileSensor waits for the file to appear
3. **process_file** - Processes the detected file
4. **cleanup_file** - Cleans up the test file

### To test:
1. Go to Airflow UI (http://localhost:8080)
2. Find `file_sensor_simple` DAG
3. Click "Trigger DAG"
4. Watch the tasks execute in sequence

---

## 📁 **DAG 2: file_sensor_manual** 
**Manual file creation for hands-on learning**

### How it works:
1. **wait_for_manual_file** - FileSensor waits for you to create a file
2. **process_manual_file** - Processes your file
3. **completion_notification** - Shows processing results

### To test:
1. Trigger the `file_sensor_manual` DAG
2. The FileSensor will start waiting (you'll see it in "running" state)
3. **Manually create the file:**

```bash
# Option 1: Using Docker exec
docker-compose exec airflow-scheduler bash -c "echo 'Hello FileSensor!' > /opt/airflow/dags/test_files/manual_data.txt"

# Option 2: Create file locally (if you have the dags folder mounted)
echo "Hello FileSensor!" > dags/test_files/manual_data.txt
echo "This is line 2" >> dags/test_files/manual_data.txt
echo "FileSensor will detect this file!" >> dags/test_files/manual_data.txt
```

4. Watch the FileSensor detect the file and trigger the next tasks!

---

## 🔧 **FileSensor Configuration Explained**

```python
wait_for_file = FileSensor(
    task_id='wait_for_file',
    filepath='/opt/airflow/dags/test_files/data.txt',  # File to monitor
    fs_conn_id='fs_default',                           # Filesystem connection
    poke_interval=10,                                  # Check every 10 seconds
    timeout=300,                                       # Give up after 5 minutes
    dag=dag
)
```

### Key Parameters:
- **filepath**: Path to the file to monitor
- **poke_interval**: How often to check (seconds)
- **timeout**: Maximum wait time (seconds)
- **fs_conn_id**: Filesystem connection ID

---

## 🎯 **Learning Objectives**

After running these DAGs, you'll understand:

1. ✅ **How FileSensor works** - Waits for files to appear
2. ✅ **Poke interval** - How often it checks
3. ✅ **Timeout handling** - What happens when files don't appear
4. ✅ **Task dependencies** - How sensors trigger downstream tasks
5. ✅ **File processing patterns** - Common file handling workflows

---

## 🔍 **Monitoring the FileSensor**

### In Airflow UI:
- **Green**: File detected, sensor succeeded
- **Yellow/Running**: Still waiting for file
- **Red**: Timeout reached, file not found

### In Logs:
- Look for "Poking for file" messages
- Check poke interval timing
- See file detection confirmation

---

## 🚀 **Next Steps**

Once you're comfortable with basic FileSensor:

1. **Try different file types** - CSV, JSON, XML
2. **Multiple files** - Wait for several files
3. **File patterns** - Use wildcards (*.csv)
4. **Different directories** - Monitor various folders
5. **Integration** - Combine with your earthquake pipeline

---

## 🛠️ **Troubleshooting**

### FileSensor stuck in running state?
- Check if the file path is correct
- Verify file permissions
- Look at the sensor logs for details

### File not being detected?
- Ensure the exact file path matches
- Check file permissions
- Verify the file actually exists

### Timeout issues?
- Increase timeout value
- Check poke_interval (too frequent can cause issues)
- Verify filesystem access

Happy learning with FileSensor! 🎉