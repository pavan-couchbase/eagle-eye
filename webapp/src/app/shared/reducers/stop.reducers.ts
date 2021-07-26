import * as eeActions from '../actions/ee.actions';
import {Action,createReducer, on} from "@ngrx/store";

export interface State {
  jobId: string,
  successMsg: string,
  errorMsg: string
}

export const initialState: State = {
  jobId: "",
  successMsg: "",
  errorMsg: ""
};

const stopReducer = createReducer(
  initialState,
  on(eeActions.Stop, (state, {jobId}) => ({
    ...state,
    jobId: jobId
  })),
  on(eeActions.StopSuccess, (state, {msg}) => ({
    ...state,
    successMsg: msg
  })),
  on(eeActions.StopFail, (state, {msg}) => ({
    ...state,
    errorMsg: msg
  }))
)

export function reducer(state: State | undefined, action: Action) {
  return stopReducer(state, action)
}
