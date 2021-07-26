import * as eeActions from '../actions/ee.actions';
import {Action,createReducer, on} from "@ngrx/store";

export interface State {
  jobId: string,
  status: any,
  error: string
}

export const initialState: State = {
  jobId: "",
  status: {},
  error: ""
};

export const statusReducer = createReducer(
  initialState,
  on(eeActions.Status, (state, {jobId}) => ({
    ...state,
    jobId: jobId
  })),
  on(eeActions.StatusSuccess, (state, {data}) => ({
    ...state,
    data: data
  })),
  on(eeActions.StatusFail, (state, {error}) => ({
    ...state,
    error: error
  }))
)

export function reducer(state: State | undefined, action: Action) {
  return statusReducer(state, action)
}
