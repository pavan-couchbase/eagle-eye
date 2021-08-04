import * as eeActions from '../actions/ee.actions';
import {Action,createReducer, on} from "@ngrx/store";

export interface State {
    jobId: string,
    iteration: number,
    successMsg: string,
    errorMsg: string
}

export const initialState: State = {
    jobId: "",
    iteration: 0,
    successMsg: "",
    errorMsg: ""
}

export const uploadSupportalReducer = createReducer(
    initialState,
    on(eeActions.UploadSupportal, (state, {request}) => ({
        ...state,
        jobid: request.jobId,
        iteration: request.iter_num
    })),
    on(eeActions.UploadSupportalSuccess, (state, {Msg}) => ({
        ...state,
        successMsg: Msg
    })),
    on(eeActions.UploadSupportalFail, (state, {Msg}) => ({
        ...state,
        errorMsg: Msg
    }))
)

export function reducer(state: State | undefined, action: Action) {
    return uploadSupportalReducer(state, action)
}