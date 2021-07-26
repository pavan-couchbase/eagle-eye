import * as eeActions from '../actions/ee.actions';
import {Action,createReducer, on} from "@ngrx/store";

export interface State {
  jobId: string,
  host: string,
  clustername: string,
  configfile: any,
  restusername: string, restpassword: string,
  sshusername: string, sshpassword: string,
  dockerhost: string,
  emails: string,
  alertfrequency: number,
  error: string
}

export const initialState: State = {
  jobId: "",
  host: "",
  clustername: "",
  configfile: {},
  restusername: "", restpassword: "",
  sshusername: "", sshpassword: "",
  dockerhost: "",
  emails: "",
  alertfrequency: 0,
  error: ""
};

const startReducer = createReducer(
  initialState,
  on(eeActions.Start, (state, {request}) => ({
    ...state,
    host: request.host,
    clustername: request.clustername,
    configfile: request.configfile,
    restusername: request.restusername, restpassword: request.restpassword,
    sshusername: request.sshusername, sshpassword: request.sshpassword,
    dockerhost: request.dockerhost,
    emails: request.emails,
    alertfrequency: request.alertfrequency
  })),
  on(eeActions.StartSuccess, (state, {jobId}) => ({
    ...state,
    jobId: jobId
  })),
  on(eeActions.StartFail, (state, {error}) => ({
    ...state,
    error: error
  }))
)

export function reducer(state: State | undefined, action: Action) {
  return startReducer(state, action)
}
