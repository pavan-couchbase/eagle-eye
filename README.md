# Eagle-Eye V2

## Components
### Server
The server has 3 main components: `app.py`, `/endpoints`, and `/util`. `app.py` is the main file for the 
server and calls all the endpoints. The endpoints directory has the files for all API endpoints. 
Adding an endpoint involves creating a file in that folder and calling it in `app.py`. The util directory
has the `eagle_eye.py` and the `task_manager.py`. The `eagle_eye.py` is a wrapper of the Eagle-Eye
V1 and reuses most of the code. The `task_manager.py` file is essentially a job. Each `task_manager` has
a `eagle-eye` instantiation. 

### Web Application
The web application components can be found in `/src/app/`. Each component has a directory, and the files
that are shared amongst components are under `/shared/`. This directory will handle the requests
and responses to the server. See https://ngrx.io/guide/store for more information.

The layout of the components (subpoint = parent component calls child component):

* appbar component
* apptab component
    * dashboard component
        * data viewer component
    * job manager component
    * server status component

## Deployment
We decided to utilize Dockers to deploy Eagle-Eye for fast and flexible deployment. Here are the steps
to use docker to deploy.

First clone the directory and navigate to the ee-v2 branch.

    git clone https://github.com/couchbaselabs/eagle-eye.git
    cd eagle-eye
    git checkout origin/ee-v2

Then, you can build the docker images. There are two images in the project (one for server and one for the webapp)

    docker build sequoiatools/ee-server ./eagle-eye/server
    docker build sequoiatools/ee-app ./eagle-eye/webapp

Once the images have both finished, run the images.

    docker run -dp 5000:5000 sequoiatools/ee-server
    docker run -dp 4200:4200 sequoiatools/ee-app

After a couple minutes, the server and the web application will be up and running!


## Development
To start the server, run the `/server/app.py` file using python3. Using PyCharm or any other IDE,
you can debug through this file and others.

To start the webapp, navigate to `/webapp` and call `ng serve`. That should be sufficient to run on
your local machine. Check the `/webapp/Dockerfile` for the command to start the webapp in production mode.

### Adding a Data Collector
1. Create a function on the server (`eagle_eye.py`)
    * Need to call `_task_init()` and definte the type of data (timeseries or static)
    * Necessary logic/code for data collector
        * wrap while loop in `try` and `except` for error logging
    * Call `_task_sleep()` at the end of the while loop
    
2. Add to the config file as well as `run_all.json` (specify necessary parameters)
    * Be sure to name data collector in config files the same as the function name in `eagle_eye.py`
    
3. Add the data collector name (same defined as in JSON) to the array in dat collectors object in `data-viewer.components.ts`
and in `dc_schema` in `job-manager.component.ts`. Do not forget to add it to `run_all.json` in the
   `job-manager/` directory.