import { useParams } from "react-router-dom";
import { Text } from "@nautobot/nautobot-ui";
import { useDispatch } from "react-redux";

import { LoadingWidget } from "@components/LoadingWidget";
import ObjectListTable from "@components/ObjectListTable";
import GenericView from "@views/generic/GenericView";
import { useGetRESTAPIQuery } from "@utils/api";
import { useEffect } from "react";
import {
    updateAppCurrentContext,
    getCurrentAppContextSelector,
} from "@utils/store";
import { useSelector } from "react-redux";
import { useSearchParams } from "react-router-dom";


export default function GenericObjectListView() {
    const { app_name, model_name } = useParams();
    const dispatch = useDispatch();
    const currentAppContext = useSelector(
        getCurrentAppContextSelector(app_name, model_name)
    );
    useEffect(() => {
        dispatch(updateAppCurrentContext(currentAppContext));
    }, [dispatch, currentAppContext]);

    let [searchParams, setSearchParams] = useSearchParams();

    const { data: headerData, isLoading: headerDataLoading } =
        useGetRESTAPIQuery({
            app_name: app_name,
            model_name: model_name,
            schema: true,
        });

    // What page are we on?
    // TODO: Pagination handling should be it's own function so it's testable
    let page_size = 50;
    let active_page_number = 0;
    let searchQuery = {
        app_name: app_name,
        model_name: model_name,
    }
    if (searchParams.get("limit")) {
        searchQuery.limit = searchParams.get("limit");
        page_size = searchParams.get("limit");
    }
    if (searchParams.get("offset")) {
        searchQuery.offset = searchParams.get("offset");
        active_page_number = searchParams.get("offset") / page_size;
    }

    const { data: listData, isLoading: listDataLoading } = useGetRESTAPIQuery(searchQuery);

    if (!app_name || !model_name) {
        return (
            <GenericView>
                <LoadingWidget />
            </GenericView>
        );
    }

    if (listDataLoading || headerDataLoading) {
        return (
            <GenericView>
                <LoadingWidget name={model_name} />
            </GenericView>
        );
    }

    if (!listData || !headerData) {
        return (
            <GenericView>
                <Text>Error loading.</Text>
            </GenericView>
        );
    }

    const transformedHeaders = Object.entries(headerData.schema.properties).map(
        ([key, value]) => {
            return { name: key, label: value.title };
        }
    );
    let defaultHeaders = headerData.view_options.list_display;

    // If list_display is not defined or empty, default to showing all headers.
    if (!defaultHeaders.length) {
        defaultHeaders = transformedHeaders;
    }

    let table_name = model_name
        .split("-")
        .map((x) => (x ? x[0].toUpperCase() + x.slice(1) : ""))
        .join(" ");
    return (
        <GenericView>
            <ObjectListTable
                tableData={listData.results}
                defaultHeaders={defaultHeaders}
                tableHeaders={transformedHeaders}
                totalCount={listData.count}
                active_page_number={active_page_number}
                page_size={page_size}
                tableTitle={table_name}
            />
        </GenericView>
    );
}
